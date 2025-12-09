---
name: frontend-dev
description: Frontend development best practices
version: 1.0
author: ReACTOR Team
allowed_tools:
  - read_file_content
  - write_file
  - modify_file
  - search_in_files
working_patterns:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.css"
  - "**/*.scss"
  - "**/*.test.tsx"
---

# Frontend Development Skill

## Overview
Guidelines and best practices for frontend development tasks.

## File Organization

When working on frontend tasks:

- Components in `src/components/`
- Styles in `src/styles/`
- Assets in `public/`
- Tests alongside components: `ComponentName.test.tsx`

## Code Style

### React Components
- Use functional components with hooks
- Proper TypeScript typing for all props
- CSS modules for scoped styles
- Destructure props in function signature
- Use memo for expensive renders

### Example
```tsx
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}

export const Button: React.FC<ButtonProps> = ({ 
  label, 
  onClick, 
  variant = 'primary' 
}) => {
  return (
    <button 
      className={`btn btn-${variant}`} 
      onClick={onClick}
    >
      {label}
    </button>
  );
};
```

## Testing
- Write unit tests for components
- Use Testing Library best practices
- Test user interactions, not implementation details
- Aim for 80%+ coverage on UI components

## Performance
- Lazy load routes and heavy components
- Optimize images (WebP, proper sizing)
- Minimize bundle size
- Use React.memo for expensive renders
