"""Performance optimization with caching and incremental parsing."""

import hashlib
import time
import pickle
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from ..core.base_parser import ASTResult, Language


@dataclass
class CacheEntry:
    """Represents a cached AST result."""
    file_path: str
    file_hash: str
    ast_result: ASTResult
    timestamp: float
    parse_time_ms: int
    access_count: int
    last_accessed: float


@dataclass
class PerformanceMetrics:
    """Performance metrics for AST operations."""
    total_parses: int
    cache_hits: int
    cache_misses: int
    average_parse_time: float
    cache_hit_rate: float
    memory_usage_mb: float
    incremental_updates: int


class ASTCache:
    """High-performance cache for AST results."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # LRU tracking
        self.metrics = PerformanceMetrics(
            total_parses=0,
            cache_hits=0,
            cache_misses=0,
            average_parse_time=0.0,
            cache_hit_rate=0.0,
            memory_usage_mb=0.0,
            incremental_updates=0
        )
    
    def get(self, file_path: str, file_hash: str) -> Optional[ASTResult]:
        """Get cached AST result if valid."""
        cache_key = self._get_cache_key(file_path, file_hash)
        
        if cache_key not in self.cache:
            self.metrics.cache_misses += 1
            return None
        
        entry = self.cache[cache_key]
        
        # Check TTL
        if time.time() - entry.timestamp > self.ttl_seconds:
            self._remove_entry(cache_key)
            self.metrics.cache_misses += 1
            return None
        
        # Check file hash (detect changes)
        if entry.file_hash != file_hash:
            self._remove_entry(cache_key)
            self.metrics.cache_misses += 1
            return None
        
        # Update access tracking
        entry.access_count += 1
        entry.last_accessed = time.time()
        self._move_to_end(cache_key)
        
        self.metrics.cache_hits += 1
        self._update_hit_rate()
        
        return entry.ast_result
    
    def put(self, file_path: str, file_hash: str, ast_result: ASTResult, parse_time_ms: int) -> None:
        """Cache AST result."""
        cache_key = self._get_cache_key(file_path, file_hash)
        
        # Create cache entry
        entry = CacheEntry(
            file_path=file_path,
            file_hash=file_hash,
            ast_result=ast_result,
            timestamp=time.time(),
            parse_time_ms=parse_time_ms,
            access_count=1,
            last_accessed=time.time()
        )
        
        # Add to cache
        self.cache[cache_key] = entry
        self.access_order.append(cache_key)
        
        # Enforce size limit
        if len(self.cache) > self.max_size:
            self._evict_lru()
        
        # Update metrics
        self.metrics.total_parses += 1
        self._update_average_parse_time(parse_time_ms)
        self._update_memory_usage()
    
    def invalidate(self, file_path: str) -> None:
        """Invalidate cache entry for specific file."""
        keys_to_remove = []
        for cache_key in self.cache:
            if cache_key.startswith(file_path + ":"):
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            self._remove_entry(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_order.clear()
        self.metrics.memory_usage_mb = 0.0
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        self._update_hit_rate()
        return self.metrics
    
    def _get_cache_key(self, file_path: str, file_hash: str) -> str:
        """Generate cache key."""
        return f"{file_path}:{file_hash}"
    
    def _remove_entry(self, cache_key: str) -> None:
        """Remove entry from cache."""
        if cache_key in self.cache:
            del self.cache[cache_key]
        if cache_key in self.access_order:
            self.access_order.remove(cache_key)
    
    def _move_to_end(self, cache_key: str) -> None:
        """Move entry to end of access order (LRU)."""
        if cache_key in self.access_order:
            self.access_order.remove(cache_key)
            self.access_order.append(cache_key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]
    
    def _update_hit_rate(self) -> None:
        """Update cache hit rate."""
        total = self.metrics.cache_hits + self.metrics.cache_misses
        self.metrics.cache_hit_rate = (self.metrics.cache_hits / total * 100) if total > 0 else 0.0
    
    def _update_average_parse_time(self, parse_time_ms: int) -> None:
        """Update average parse time."""
        if self.metrics.total_parses == 1:
            self.metrics.average_parse_time = parse_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics.average_parse_time = (
                alpha * parse_time_ms + 
                (1 - alpha) * self.metrics.average_parse_time
            )
    
    def _update_memory_usage(self) -> None:
        """Estimate memory usage."""
        try:
            # Rough estimation of cache size in memory
            total_size = 0
            for entry in self.cache.values():
                # Serialize entry to estimate size
                entry_size = len(pickle.dumps(entry.ast_result))
                total_size += entry_size
            
            self.metrics.memory_usage_mb = total_size / (1024 * 1024)
        except Exception:
            self.metrics.memory_usage_mb = 0.0


class IncrementalParser:
    """Incremental parser for updating ASTs efficiently."""
    
    def __init__(self, cache: ASTCache):
        self.cache = cache
        self.file_states: Dict[str, Dict] = {}  # Track file modification states
    
    def parse_incremental(self, file_path: str, content: str, parser_func) -> ASTResult:
        """Parse file incrementally if possible."""
        file_hash = self._calculate_file_hash(content)
        
        # Check if we have cached result
        cached_result = self.cache.get(file_path, file_hash)
        if cached_result:
            return cached_result
        
        # Check if we can do incremental update
        if self._can_incremental_update(file_path, file_hash):
            return self._update_incremental(file_path, content, parser_func)
        
        # Full parse required
        start_time = time.time()
        ast_result = parser_func(file_path, content)
        parse_time_ms = int((time.time() - start_time) * 1000)
        
        # Cache the result
        self.cache.put(file_path, file_hash, ast_result, parse_time_ms)
        
        # Update file state
        self._update_file_state(file_path, content, ast_result)
        
        return ast_result
    
    def _calculate_file_hash(self, content: str) -> str:
        """Calculate hash of file content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _can_incremental_update(self, file_path: str, file_hash: str) -> bool:
        """Check if incremental update is possible."""
        if file_path not in self.file_states:
            return False
        
        previous_state = self.file_states[file_path]
        
        # Check if file hash changed significantly
        if previous_state.get('hash') != file_hash:
            # Could do more sophisticated diff analysis here
            return False
        
        return True
    
    def _update_incremental(self, file_path: str, content: str, parser_func) -> ASTResult:
        """Perform incremental update of AST."""
        # Simplified incremental update - in real implementation would do diff-based updates
        start_time = time.time()
        ast_result = parser_func(file_path, content)
        parse_time_ms = int((time.time() - start_time) * 1000)
        
        file_hash = self._calculate_file_hash(content)
        self.cache.put(file_path, file_hash, ast_result, parse_time_ms)
        
        # Update metrics
        self.cache.metrics.incremental_updates += 1
        
        return ast_result
    
    def _update_file_state(self, file_path: str, content: str, ast_result: ASTResult) -> None:
        """Update file state for incremental parsing."""
        file_hash = self._calculate_file_hash(content)
        
        self.file_states[file_path] = {
            'hash': file_hash,
            'timestamp': time.time(),
            'function_count': len(ast_result.functions or []),
            'class_count': len(ast_result.classes or []),
            'import_count': len(ast_result.imports or [])
        }


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self, cache_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = ASTCache(cache_size, ttl_seconds)
        self.incremental_parser = IncrementalParser(self.cache)
        self.parallel_workers = 4  # Configurable
        self.batch_size = 50  # Files per batch
    
    def optimize_parse(self, file_path: str, content: str, parser_func) -> ASTResult:
        """Optimized parsing with caching and incremental updates."""
        return self.incremental_parser.parse_incremental(file_path, content, parser_func)
    
    def optimize_batch_parse(self, file_paths: List[str], parser_func) -> List[ASTResult]:
        """Optimized batch parsing with parallel processing."""
        import concurrent.futures
        
        results = []
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(file_paths), self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
                # Submit tasks
                future_to_path = {}
                for file_path in batch:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        future = executor.submit(
                            self.optimize_parse, 
                            file_path, 
                            content, 
                            parser_func
                        )
                        future_to_path[future] = file_path
                    except Exception as e:
                        # Create error result for files that can't be read
                        error_result = ASTResult(
                            success=False,
                            language=Language.PYTHON,  # Default
                            error=f"Cannot read file: {str(e)}"
                        )
                        results.append(error_result)
                
                # Collect results
                for future in concurrent.futures.as_completed(future_to_path):
                    file_path = future_to_path[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        error_result = ASTResult(
                            success=False,
                            language=Language.PYTHON,  # Default
                            error=f"Parse failed: {str(e)}"
                        )
                        results.append(error_result)
        
        return results
    
    def precompute_common_patterns(self, file_paths: List[str]) -> None:
        """Precompute common patterns for frequently accessed files."""
        # Identify most frequently accessed files
        file_access_counts = {}
        for file_path in file_paths:
            file_access_counts[file_path] = file_access_counts.get(file_path, 0) + 1
        
        # Sort by access frequency
        sorted_files = sorted(file_access_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Pre-warm cache for top files
        for file_path, _ in sorted_files[:10]:  # Top 10 files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_hash = self.incremental_parser._calculate_file_hash(content)
                
                # Check if already cached
                if not self.cache.get(file_path, file_hash):
                    # Would parse and cache here
                    pass  # Would need parser function
                    
            except Exception:
                continue  # Skip files that can't be read
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage and return optimization report."""
        optimizations = []
        
        # Cache cleanup
        if self.cache.metrics.memory_usage_mb > 100:  # 100MB threshold
            # Remove old entries
            current_time = time.time()
            keys_to_remove = []
            
            for cache_key, entry in self.cache.cache.items():
                if current_time - entry.timestamp > self.cache.ttl_seconds / 2:
                    keys_to_remove.append(cache_key)
            
            for key in keys_to_remove:
                self.cache._remove_entry(key)
            
            optimizations.append(f"Removed {len(keys_to_remove)} old cache entries")
        
        # Reduce cache size if memory usage is high
        if self.cache.metrics.memory_usage_mb > 200:  # 200MB threshold
            old_size = len(self.cache.cache)
            target_size = int(old_size * 0.7)  # Reduce to 70%
            
            # Remove LRU entries
            while len(self.cache.cache) > target_size:
                if self.cache.access_order:
                    lru_key = self.cache.access_order.pop(0)
                    if lru_key in self.cache.cache:
                        del self.cache.cache[lru_key]
            
            optimizations.append(f"Reduced cache size from {old_size} to {target_size}")
        
        return {
            "optimizations": optimizations,
            "memory_before": self.cache.metrics.memory_usage_mb,
            "memory_after": self.cache.metrics.memory_usage_mb,
            "cache_size": len(self.cache.cache),
            "hit_rate": self.cache.metrics.cache_hit_rate
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        metrics = self.cache.get_metrics()
        
        return {
            "cache_metrics": {
                "total_entries": len(self.cache.cache),
                "max_size": self.cache.max_size,
                "hit_rate": f"{metrics.cache_hit_rate:.2f}%",
                "total_hits": metrics.cache_hits,
                "total_misses": metrics.cache_misses,
                "memory_usage_mb": metrics.memory_usage_mb
            },
            "parsing_metrics": {
                "total_parses": metrics.total_parses,
                "average_parse_time_ms": metrics.average_parse_time,
                "incremental_updates": metrics.incremental_updates
            },
            "optimization_settings": {
                "parallel_workers": self.parallel_workers,
                "batch_size": self.batch_size,
                "ttl_seconds": self.cache.ttl_seconds
            },
            "recommendations": self._generate_performance_recommendations(metrics)
        }
    
    def _generate_performance_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Cache hit rate recommendations
        if metrics.cache_hit_rate < 50:
            recommendations.append("Low cache hit rate. Consider increasing cache size or TTL.")
        elif metrics.cache_hit_rate < 75:
            recommendations.append("Moderate cache hit rate. Review cache invalidation strategy.")
        
        # Memory usage recommendations
        if metrics.memory_usage_mb > 200:
            recommendations.append("High memory usage. Consider reducing cache size or implementing cache compression.")
        
        # Parse time recommendations
        if metrics.average_parse_time > 1000:  # 1 second
            recommendations.append("Slow parse times. Consider optimizing parsers or using incremental parsing.")
        
        # Incremental update recommendations
        if metrics.incremental_updates < metrics.total_parses * 0.3:
            recommendations.append("Low incremental update usage. Review file change detection logic.")
        
        return recommendations
    
    def save_cache_state(self, file_path: str) -> bool:
        """Save cache state to disk for persistence."""
        try:
            cache_state = {
                'cache': self.cache.cache,
                'access_order': self.cache.access_order,
                'file_states': self.incremental_parser.file_states,
                'metrics': {
                    'total_parses': self.cache.metrics.total_parses,
                    'cache_hits': self.cache.metrics.cache_hits,
                    'cache_misses': self.cache.metrics.cache_misses,
                    'average_parse_time': self.cache.metrics.average_parse_time,
                    'incremental_updates': self.cache.metrics.incremental_updates
                }
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(cache_state, f)
            
            return True
        except Exception as e:
            print(f"Error saving cache state: {e}")
            return False
    
    def load_cache_state(self, file_path: str) -> bool:
        """Load cache state from disk."""
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'rb') as f:
                cache_state = pickle.load(f)
            
            # Restore cache
            self.cache.cache = cache_state.get('cache', {})
            self.cache.access_order = cache_state.get('access_order', [])
            self.incremental_parser.file_states = cache_state.get('file_states', {})
            
            # Restore metrics
            metrics_data = cache_state.get('metrics', {})
            self.cache.metrics.total_parses = metrics_data.get('total_parses', 0)
            self.cache.metrics.cache_hits = metrics_data.get('cache_hits', 0)
            self.cache.metrics.cache_misses = metrics_data.get('cache_misses', 0)
            self.cache.metrics.average_parse_time = metrics_data.get('average_parse_time', 0.0)
            self.cache.metrics.incremental_updates = metrics_data.get('incremental_updates', 0)
            
            # Update derived metrics
            self.cache._update_hit_rate()
            self.cache._update_memory_usage()
            
            return True
        except Exception as e:
            print(f"Error loading cache state: {e}")
            return False