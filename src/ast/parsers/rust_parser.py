"""Rust language AST parser implementation."""

import asyncio
import subprocess
import tempfile
import os
import time
import json
from typing import Dict, List, Any, Optional

from ..core.base_parser import (
    BaseParser,
    ASTResult,
    Language,
    Parameter,
    Property,
    Method,
    Function,
    Class,
    Import,
    Variable,
)


class RustParser(BaseParser):
    """Rust language parser using syn crate."""

    def __init__(self):
        super().__init__()
        self.language = Language.RUST

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return [".rs"]

    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """Parse Rust file and extract AST information."""
        start_time = time.time()

        try:
            # Use syn via a temporary Rust program
            ast_data = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_rust_ast, file_path, content
            )

            # Convert to ASTResult
            functions = self._convert_functions(ast_data.get("functions", []))
            classes = self._convert_structs(ast_data.get("structs", []))
            classes.extend(self._convert_traits(ast_data.get("traits", [])))
            classes.extend(self._convert_enums(ast_data.get("enums", [])))
            imports = self._convert_imports(ast_data.get("imports", []))
            variables = self._convert_variables(ast_data.get("variables", []))

            parse_time = int((time.time() - start_time) * 1000)

            return ASTResult(
                success=True,
                language=self.language,
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                metadata={
                    "crate_name": ast_data.get("crate_name", ""),
                    "modules": ast_data.get("modules", []),
                    "macros": ast_data.get("macros", []),
                    "traits": ast_data.get("traits", []),
                    "impl_blocks": ast_data.get("impl_blocks", []),
                    "unsafe_blocks": ast_data.get("unsafe_blocks", []),
                    "lifetimes": ast_data.get("lifetimes", []),
                },
                parse_time_ms=parse_time,
            )

        except Exception as e:
            parse_time = int((time.time() - start_time) * 1000)
            return ASTResult(
                success=False,
                language=self.language,
                error=str(e),
                parse_time_ms=parse_time,
            )

    async def parse_batch(self, file_paths: List[str]) -> List[ASTResult]:
        """Parse multiple files in parallel."""
        tasks = []
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tasks.append(self.parse_file(file_path, content))
            except Exception as e:

                async def error_result():
                    return ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Cannot read file: {str(e)}",
                    )

                tasks.append(error_result())

        return await asyncio.gather(*tasks)

    def _extract_rust_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract AST information using Rust's syn crate."""
        # Create a temporary Rust program to parse the file
        rust_parser_code = """
use syn::{Item, ItemFn, ItemStruct, ItemEnum, ItemTrait, ItemMod, ItemUse, ItemImpl, ItemConst, ItemStatic};
use syn::{Attribute, Signature, Fields, Variant, Generics, WhereClause, TraitBound, Lifetime, TypeParam, ConstParam};
use quote::quote;
use std::collections::HashMap;
use std::fs;
use std::env;

#[derive(Debug, serde::Serialize)]
struct FunctionInfo {
    name: String,
    parameters: Vec<ParamInfo>,
    return_type: String,
    line: usize,
    is_exported: bool,
    is_unsafe: bool,
    is_async: bool,
    generics: Vec<String>,
    lifetimes: Vec<String>,
    where_clause: Option<String>,
    doc: String,
    attributes: Vec<String>,
}

#[derive(Debug, serde::Serialize)]
struct ParamInfo {
    name: String,
    type_name: String,
    is_mut: bool,
    is_reference: bool,
    is_lifetime: bool,
}

#[derive(Debug, serde::Serialize)]
struct StructInfo {
    name: String,
    fields: Vec<FieldInfo>,
    line: usize,
    is_exported: bool,
    generics: Vec<String>,
    lifetimes: Vec<String>,
    where_clause: Option<String>,
    doc: String,
    attributes: Vec<String>,
    is_tuple: bool,
}

#[derive(Debug, serde::Serialize)]
struct FieldInfo {
    name: String,
    type_name: String,
    is_pub: bool,
    is_mut: bool,
}

#[derive(Debug, serde::Serialize)]
struct EnumInfo {
    name: String,
    variants: Vec<VariantInfo>,
    line: usize,
    is_exported: bool,
    generics: Vec<String>,
    lifetimes: Vec<String>,
    where_clause: Option<String>,
    doc: String,
    attributes: Vec<String>,
}

#[derive(Debug, serde::Serialize)]
struct VariantInfo {
    name: String,
    fields: Vec<FieldInfo>,
    is_tuple: bool,
    is_unit: bool,
}

#[derive(Debug, serde::Serialize)]
struct TraitInfo {
    name: String,
    methods: Vec<FunctionInfo>,
    line: usize,
    is_exported: bool,
    generics: Vec<String>,
    lifetimes: Vec<String>,
    where_clause: Option<String>,
    supertraits: Vec<String>,
    doc: String,
    attributes: Vec<String>,
}

#[derive(Debug, serde::Serialize)]
struct ImportInfo {
    path: String,
    name: Option<String>,
    alias: Option<String>,
    line: usize,
    is_glob: bool,
    attributes: Vec<String>,
}

#[derive(Debug, serde::Serialize)]
struct VariableInfo {
    name: String,
    type_name: String,
    value: Option<String>,
    line: usize,
    is_exported: bool,
    is_const: bool,
    is_static: bool,
    doc: String,
    attributes: Vec<String>,
}

#[derive(Debug, serde::Serialize)]
struct ImplInfo {
    target_type: String,
    trait_name: Option<String>,
    methods: Vec<FunctionInfo>,
    line: usize,
    is_unsafe: bool,
    generics: Vec<String>,
    lifetimes: Vec<String>,
    where_clause: Option<String>,
}

#[derive(Debug, serde::Serialize)]
struct MacroInfo {
    name: String,
    content: String,
    line: usize,
    is_exported: bool,
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: {} <filename>", args[0]);
        std::process::exit(1);
    }

    let filename = &args[1];
    let content = fs::read_to_string(filename).expect("Could not read file");
    
    let syntax = syn::parse_file(&content).expect("Unable to parse file");
    
    let mut result = serde_json::json!({
        "functions": Vec::<FunctionInfo>::new(),
        "structs": Vec::<StructInfo>::new(),
        "enums": Vec::<EnumInfo>::new(),
        "traits": Vec::<TraitInfo>::new(),
        "imports": Vec::<ImportInfo>::new(),
        "variables": Vec::<VariableInfo>::new(),
        "impl_blocks": Vec::<ImplInfo>::new(),
        "modules": Vec::<String>::new(),
        "macros": Vec::<MacroInfo>::new(),
        "unsafe_blocks": Vec::<usize>::new(),
        "lifetimes": Vec::<String>::new(),
        "crate_name": ""
    });

    for item in syntax.items {
        match item {
            Item::Fn(item_fn) => {
                let func_info = extract_function_info(&item_fn);
                result["functions"].as_array_mut().unwrap().push(serde_json::to_value(func_info).unwrap());
            }
            Item::Struct(item_struct) => {
                let struct_info = extract_struct_info(&item_struct);
                result["structs"].as_array_mut().unwrap().push(serde_json::to_value(struct_info).unwrap());
            }
            Item::Enum(item_enum) => {
                let enum_info = extract_enum_info(&item_enum);
                result["enums"].as_array_mut().unwrap().push(serde_json::to_value(enum_info).unwrap());
            }
            Item::Trait(item_trait) => {
                let trait_info = extract_trait_info(&item_trait);
                result["traits"].as_array_mut().unwrap().push(serde_json::to_value(trait_info).unwrap());
            }
            Item::Use(item_use) => {
                let import_info = extract_import_info(&item_use);
                result["imports"].as_array_mut().unwrap().push(serde_json::to_value(import_info).unwrap());
            }
            Item::Const(item_const) => {
                let var_info = extract_variable_info_const(&item_const);
                result["variables"].as_array_mut().unwrap().push(serde_json::to_value(var_info).unwrap());
            }
            Item::Static(item_static) => {
                let var_info = extract_variable_info_static(&item_static);
                result["variables"].as_array_mut().unwrap().push(serde_json::to_value(var_info).unwrap());
            }
            Item::Impl(item_impl) => {
                let impl_info = extract_impl_info(&item_impl);
                result["impl_blocks"].as_array_mut().unwrap().push(serde_json::to_value(impl_info).unwrap());
            }
            Item::Mod(item_mod) => {
                if let Some(ident) = item_mod.ident {
                    result["modules"].as_array_mut().unwrap().push(serde_json::Value::String(ident.to_string()));
                }
            }
            Item::Macro(item_macro) => {
                let macro_info = extract_macro_info(&item_macro);
                result["macros"].as_array_mut().unwrap().push(serde_json::to_value(macro_info).unwrap());
            }
            _ => {}
        }
    }

    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}

fn extract_function_info(item_fn: &ItemFn) -> FunctionInfo {
    let sig = &item_fn.sig;
    let mut parameters = Vec::new();
    
    for input in &sig.inputs {
        if let syn::FnArg::Typed(pat_type) = input {
            if let syn::Pat::Ident(pat_ident) = &*pat_type.pat {
                let param_info = ParamInfo {
                    name: pat_ident.ident.to_string(),
                    type_name: quote!(#pat_type.ty).to_string(),
                    is_mut: pat_ident.mutability.is_some(),
                    is_reference: matches!(&*pat_type.ty, syn::Type::Reference(_)),
                    is_lifetime: false,
                };
                parameters.push(param_info);
            }
        }
    }

    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    
    for param in &sig.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    FunctionInfo {
        name: sig.ident.to_string(),
        parameters,
        return_type: match &sig.output {
            syn::ReturnType::Default => "()".to_string(),
            syn::ReturnType::Type(_, ty) => quote!(#ty).to_string(),
        },
        line: item_fn.span().start().line,
        is_exported: item_fn.vis == syn::Visibility::Public(crate::Token![pub](item_fn.span())),
        is_unsafe: sig.unsafety.is_some(),
        is_async: sig.asyncness.is_some(),
        generics,
        lifetimes,
        where_clause: sig.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
        doc: extract_doc(&item_fn.attrs),
        attributes: extract_attributes(&item_fn.attrs),
    }
}

fn extract_struct_info(item_struct: &ItemStruct) -> StructInfo {
    let mut fields = Vec::new();
    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    
    for param in &item_struct.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    let is_tuple = matches!(item_struct.fields, syn::Fields::Unnamed(_));
    
    match &item_struct.fields {
        syn::Fields::Named(fields_named) => {
            for field in &fields_named.named {
                if let Some(ident) = &field.ident {
                    let field_info = FieldInfo {
                        name: ident.to_string(),
                        type_name: quote!(#field.ty).to_string(),
                        is_pub: field.vis == syn::Visibility::Public(crate::Token![pub](field.span())),
                        is_mut: false,
                    };
                    fields.push(field_info);
                }
            }
        }
        syn::Fields::Unnamed(fields_unnamed) => {
            for (index, field) in fields_unnamed.unnamed.iter().enumerate() {
                let field_info = FieldInfo {
                    name: format!("{}", index),
                    type_name: quote!(#field.ty).to_string(),
                    is_pub: field.vis == syn::Visibility::Public(crate::Token![pub](field.span())),
                    is_mut: false,
                };
                fields.push(field_info);
            }
        }
        syn::Fields::Unit => {}
    }

    StructInfo {
        name: item_struct.ident.to_string(),
        fields,
        line: item_struct.span().start().line,
        is_exported: item_struct.vis == syn::Visibility::Public(crate::Token![pub](item_struct.span())),
        generics,
        lifetimes,
        where_clause: item_struct.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
        doc: extract_doc(&item_struct.attrs),
        attributes: extract_attributes(&item_struct.attrs),
        is_tuple,
    }
}

fn extract_enum_info(item_enum: &ItemEnum) -> EnumInfo {
    let mut variants = Vec::new();
    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    
    for param in &item_enum.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    for variant in &item_enum.variants {
        let mut variant_fields = Vec::new();
        let is_tuple = matches!(variant.fields, syn::Fields::Unnamed(_));
        let is_unit = matches!(variant.fields, syn::Fields::Unit);
        
        match &variant.fields {
            syn::Fields::Named(fields_named) => {
                for field in &fields_named.named {
                    if let Some(ident) = &field.ident {
                        let field_info = FieldInfo {
                            name: ident.to_string(),
                            type_name: quote!(#field.ty).to_string(),
                            is_pub: field.vis == syn::Visibility::Public(crate::Token![pub](field.span())),
                            is_mut: false,
                        };
                        variant_fields.push(field_info);
                    }
                }
            }
            syn::Fields::Unnamed(fields_unnamed) => {
                for (index, field) in fields_unnamed.unnamed.iter().enumerate() {
                    let field_info = FieldInfo {
                        name: format!("{}", index),
                        type_name: quote!(#field.ty).to_string(),
                        is_pub: field.vis == syn::Visibility::Public(crate::Token![pub](field.span())),
                        is_mut: false,
                    };
                    variant_fields.push(field_info);
                }
            }
            syn::Fields::Unit => {}
        }
        
        let variant_info = VariantInfo {
            name: variant.ident.to_string(),
            fields: variant_fields,
            is_tuple,
            is_unit,
        };
        variants.push(variant_info);
    }

    EnumInfo {
        name: item_enum.ident.to_string(),
        variants,
        line: item_enum.span().start().line,
        is_exported: item_enum.vis == syn::Visibility::Public(crate::Token![pub](item_enum.span())),
        generics,
        lifetimes,
        where_clause: item_enum.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
        doc: extract_doc(&item_enum.attrs),
        attributes: extract_attributes(&item_enum.attrs),
    }
}

fn extract_trait_info(item_trait: &ItemTrait) -> TraitInfo {
    let mut methods = Vec::new();
    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    let mut supertraits = Vec::new();
    
    for param in &item_trait.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    for bound in &item_trait.supertraits {
        supertraits.push(quote!(#bound).to_string());
    }

    for item in &item_trait.items {
        if let syn::TraitItem::Fn(method) = item {
            let func_info = extract_function_info_from_trait_method(method);
            methods.push(func_info);
        }
    }

    TraitInfo {
        name: item_trait.ident.to_string(),
        methods,
        line: item_trait.span().start().line,
        is_exported: item_trait.vis == syn::Visibility::Public(crate::Token![pub](item_trait.span())),
        generics,
        lifetimes,
        where_clause: item_trait.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
        supertraits,
        doc: extract_doc(&item_trait.attrs),
        attributes: extract_attributes(&item_trait.attrs),
    }
}

fn extract_function_info_from_trait_method(method: &syn::TraitItemFn) -> FunctionInfo {
    let sig = &method.sig;
    let mut parameters = Vec::new();
    
    for input in &sig.inputs {
        if let syn::FnArg::Typed(pat_type) = input {
            if let syn::Pat::Ident(pat_ident) = &*pat_type.pat {
                let param_info = ParamInfo {
                    name: pat_ident.ident.to_string(),
                    type_name: quote!(#pat_type.ty).to_string(),
                    is_mut: pat_ident.mutability.is_some(),
                    is_reference: matches!(&*pat_type.ty, syn::Type::Reference(_)),
                    is_lifetime: false,
                };
                parameters.push(param_info);
            }
        }
    }

    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    
    for param in &sig.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    FunctionInfo {
        name: sig.ident.to_string(),
        parameters,
        return_type: match &sig.output {
            syn::ReturnType::Default => "()".to_string(),
            syn::ReturnType::Type(_, ty) => quote!(#ty).to_string(),
        },
        line: method.span().start().line,
        is_exported: true, // Trait methods are public by default
        is_unsafe: sig.unsafety.is_some(),
        is_async: sig.asyncness.is_some(),
        generics,
        lifetimes,
        where_clause: sig.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
        doc: extract_doc(&method.attrs),
        attributes: extract_attributes(&method.attrs),
    }
}

fn extract_import_info(item_use: &ItemUse) -> ImportInfo {
    let path = quote!(#item_use.tree).to_string();
    let is_glob = path.contains("*");
    
    ImportInfo {
        path,
        name: None,
        alias: None,
        line: item_use.span().start().line,
        is_glob,
        attributes: extract_attributes(&item_use.attrs),
    }
}

fn extract_variable_info_const(item_const: &ItemConst) -> VariableInfo {
    VariableInfo {
        name: item_const.ident.to_string(),
        type_name: quote!(#item_const.ty).to_string(),
        value: Some(quote!(#item_const.expr).to_string()),
        line: item_const.span().start().line,
        is_exported: item_const.vis == syn::Visibility::Public(crate::Token![pub](item_const.span())),
        is_const: true,
        is_static: false,
        doc: extract_doc(&item_const.attrs),
        attributes: extract_attributes(&item_const.attrs),
    }
}

fn extract_variable_info_static(item_static: &ItemStatic) -> VariableInfo {
    VariableInfo {
        name: item_static.ident.to_string(),
        type_name: quote!(#item_static.ty).to_string(),
        value: Some(quote!(#item_static.expr).to_string()),
        line: item_static.span().start().line,
        is_exported: item_static.vis == syn::Visibility::Public(crate::Token![pub](item_static.span())),
        is_const: false,
        is_static: true,
        doc: extract_doc(&item_static.attrs),
        attributes: extract_attributes(&item_static.attrs),
    }
}

fn extract_impl_info(item_impl: &ItemImpl) -> ImplInfo {
    let target_type = quote!(#item_impl.self_ty).to_string();
    let trait_name = item_impl.trait_.as_ref().map(|(_, path, _)| quote!(#path).to_string());
    let mut methods = Vec::new();
    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    
    for param in &item_impl.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    for item in &item_impl.items {
        if let syn::ImplItem::Fn(method) = item {
            let func_info = extract_function_info_from_impl_method(method);
            methods.push(func_info);
        }
    }

    ImplInfo {
        target_type,
        trait_name,
        methods,
        line: item_impl.span().start().line,
        is_unsafe: item_impl.unsafety.is_some(),
        generics,
        lifetimes,
        where_clause: item_impl.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
    }
}

fn extract_function_info_from_impl_method(method: &syn::ImplItemFn) -> FunctionInfo {
    let sig = &method.sig;
    let mut parameters = Vec::new();
    
    for input in &sig.inputs {
        if let syn::FnArg::Typed(pat_type) = input {
            if let syn::Pat::Ident(pat_ident) = &*pat_type.pat {
                let param_info = ParamInfo {
                    name: pat_ident.ident.to_string(),
                    type_name: quote!(#pat_type.ty).to_string(),
                    is_mut: pat_ident.mutability.is_some(),
                    is_reference: matches!(&*pat_type.ty, syn::Type::Reference(_)),
                    is_lifetime: false,
                };
                parameters.push(param_info);
            }
        }
    }

    let mut generics = Vec::new();
    let mut lifetimes = Vec::new();
    
    for param in &sig.generics.params {
        match param {
            syn::GenericParam::Type(type_param) => {
                generics.push(type_param.ident.to_string());
            }
            syn::GenericParam::Lifetime(lifetime_def) => {
                lifetimes.push(lifetime_def.lifetime.to_string());
            }
            syn::GenericParam::Const(const_param) => {
                generics.push(const_param.ident.to_string());
            }
        }
    }

    FunctionInfo {
        name: sig.ident.to_string(),
        parameters,
        return_type: match &sig.output {
            syn::ReturnType::Default => "()".to_string(),
            syn::ReturnType::Type(_, ty) => quote!(#ty).to_string(),
        },
        line: method.span().start().line,
        is_exported: method.vis == syn::Visibility::Public(crate::Token![pub](method.span())),
        is_unsafe: sig.unsafety.is_some(),
        is_async: sig.asyncness.is_some(),
        generics,
        lifetimes,
        where_clause: sig.generics.where_clause.as_ref().map(|w| quote!(#w).to_string()),
        doc: extract_doc(&method.attrs),
        attributes: extract_attributes(&method.attrs),
    }
}

fn extract_macro_info(item_macro: &syn::ItemMacro) -> MacroInfo {
    let name = if let Some(ident) = &item_macro.ident {
        ident.to_string()
    } else {
        "macro_rules".to_string()
    };
    
    MacroInfo {
        name,
        content: quote!(#item_macro.mac).to_string(),
        line: item_macro.span().start().line,
        is_exported: item_macro.vis == syn::Visibility::Public(crate::Token![pub](item_macro.span())),
    }
}

fn extract_doc(attrs: &[Attribute]) -> String {
    let mut doc_lines = Vec::new();
    for attr in attrs {
        if attr.path().is_ident("doc") {
            if let Ok(meta) = attr.meta.require_name_value() {
                if let syn::Expr::Lit(syn::ExprLit { lit: syn::Lit::Str(lit_str), .. }) = &meta.value {
                    doc_lines.push(lit_str.value());
                }
            }
        }
    }
    doc_lines.join("\\n")
}

fn extract_attributes(attrs: &[Attribute]) -> Vec<String> {
    attrs.iter().map(|attr| quote!(#attr).to_string()).collect()
}
"""

        # Create Cargo.toml for the parser
        cargo_toml = """
[package]
name = "rust_ast_parser"
version = "0.1.0"
edition = "2021"

[dependencies]
syn = { version = "2.0", features = ["full", "extra-traits"] }
quote = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
"""

        # Create temporary directory for Rust project
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write Cargo.toml
            with open(os.path.join(temp_dir, "Cargo.toml"), "w") as f:
                f.write(cargo_toml)

            # Create src directory
            src_dir = os.path.join(temp_dir, "src")
            os.makedirs(src_dir)

            # Write main.rs
            with open(os.path.join(src_dir, "main.rs"), "w") as f:
                f.write(rust_parser_code)

            # Write the target Rust file
            target_file = os.path.join(src_dir, "target.rs")
            with open(target_file, "w") as f:
                f.write(content)

            try:
                # Run the Rust parser
                result = subprocess.run(
                    ["cargo", "run", "--bin", "rust_ast_parser", target_file],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    raise Exception(f"Rust parser failed: {result.stderr}")

            except subprocess.TimeoutExpired:
                raise Exception("Rust parser timed out")

    def _convert_functions(self, functions_data: List[Dict]) -> List[Function]:
        """Convert function data to Function objects."""
        functions = []
        for func_data in functions_data:
            parameters = []
            for param_data in func_data.get("parameters", []):
                parameters.append(
                    Parameter(
                        name=param_data["name"],
                        type_hint=param_data["type_name"],
                        default_value=None,
                        is_optional=False,
                        docstring=None,
                    )
                )

            functions.append(
                Function(
                    name=func_data["name"],
                    parameters=parameters,
                    return_type=func_data["return_type"],
                    decorators=func_data.get("attributes", []),
                    docstring=func_data.get("doc", ""),
                    line_number=func_data["line"],
                    complexity_score=1,
                    is_async=func_data.get("is_async", False),
                    is_method=False,
                    class_name=None,
                )
            )

        return functions

    def _convert_structs(self, structs_data: List[Dict]) -> List[Class]:
        """Convert struct data to Class objects."""
        classes = []
        for struct_data in structs_data:
            properties = []
            for field_data in struct_data.get("fields", []):
                properties.append(
                    Property(
                        name=field_data["name"],
                        type_hint=field_data["type_name"],
                        line_number=struct_data["line"],
                        default_value=None,
                        access_level=(
                            "public" if field_data.get("is_pub", False) else "private"
                        ),
                        docstring=None,
                        is_property=True,
                    )
                )

            classes.append(
                Class(
                    name=struct_data["name"],
                    base_classes=[],
                    methods=[],
                    properties=properties,
                    decorators=struct_data.get("attributes", []),
                    docstring=struct_data.get("doc", ""),
                    line_number=struct_data["line"],
                    is_abstract=False,
                    access_level=(
                        "public" if struct_data.get("is_exported", False) else "private"
                    ),
                )
            )

        return classes

    def _convert_traits(self, traits_data: List[Dict]) -> List[Class]:
        """Convert trait data to Class objects."""
        classes = []
        for trait_data in traits_data:
            methods = []
            for method_data in trait_data.get("methods", []):
                parameters = []
                for param_data in method_data.get("parameters", []):
                    parameters.append(
                        Parameter(
                            name=param_data["name"],
                            type_hint=param_data["type_name"],
                            default_value=None,
                            is_optional=False,
                            docstring=None,
                        )
                    )

                methods.append(
                    Method(
                        name=method_data["name"],
                        parameters=parameters,
                        return_type=method_data["return_type"],
                        decorators=method_data.get("attributes", []),
                        docstring=method_data.get("doc", ""),
                        line_number=method_data["line"],
                        access_level="public",
                        is_static=False,
                        is_async=method_data.get("is_async", False),
                    )
                )

            classes.append(
                Class(
                    name=trait_data["name"],
                    base_classes=trait_data.get("supertraits", []),
                    methods=methods,
                    properties=[],
                    decorators=trait_data.get("attributes", []),
                    docstring=trait_data.get("doc", ""),
                    line_number=trait_data["line"],
                    is_abstract=True,
                    access_level=(
                        "public" if trait_data.get("is_exported", False) else "private"
                    ),
                )
            )

        return classes

    def _convert_enums(self, enums_data: List[Dict]) -> List[Class]:
        """Convert enum data to Class objects."""
        classes = []
        for enum_data in enums_data:
            # Convert enum variants to methods for representation
            methods = []
            for variant_data in enum_data.get("variants", []):
                methods.append(
                    Method(
                        name=variant_data["name"],
                        parameters=[],
                        return_type="Self",
                        decorators=[],
                        docstring="",
                        line_number=enum_data["line"],
                        access_level="public",
                        is_static=True,
                        is_async=False,
                    )
                )

            classes.append(
                Class(
                    name=enum_data["name"],
                    base_classes=[],
                    methods=methods,
                    properties=[],
                    decorators=enum_data.get("attributes", []),
                    docstring=enum_data.get("doc", ""),
                    line_number=enum_data["line"],
                    is_abstract=False,
                    access_level=(
                        "public" if enum_data.get("is_exported", False) else "private"
                    ),
                )
            )

        return classes

    def _convert_imports(self, imports_data: List[Dict]) -> List[Import]:
        """Convert import data to Import objects."""
        imports = []
        for import_data in imports_data:
            imports.append(
                Import(
                    module=import_data["path"],
                    name=import_data.get("name", ""),
                    alias=import_data.get("alias", ""),
                    line_number=import_data["line"],
                    import_type="use",
                    is_relative=import_data["path"].starts_with("crate::")
                    or import_data["path"].starts_with("super::"),
                    is_standard_library=self._is_standard_library(import_data["path"]),
                )
            )

        return imports

    def _convert_variables(self, variables_data: List[Dict]) -> List[Variable]:
        """Convert variable data to Variable objects."""
        variables = []
        for var_data in variables_data:
            variables.append(
                Variable(
                    name=var_data["name"],
                    type_hint=var_data["type_name"],
                    default_value=var_data.get("value", ""),
                    line_number=var_data["line"],
                    is_global=True,
                    is_constant=var_data.get("is_const", False),
                )
            )

        return variables

    def _is_standard_library(self, import_path: str) -> bool:
        """Check if import is from Rust standard library."""
        std_crates = {
            "std",
            "core",
            "alloc",
            "proc_macro",
            "test",
            "vec",
            "string",
            "collections",
            "hash_map",
            "hash_set",
            "option",
            "result",
            "cell",
            "rc",
            "sync",
            "arc",
            "box",
            "iter",
            "slice",
            "str",
            "char",
            "num",
            "io",
            "fs",
            "path",
            "env",
            "process",
            "thread",
            "time",
            "net",
            "os",
            "ffi",
            "fmt",
            "error",
        }

        # Check if it starts with std::, core::, or is a direct std crate
        parts = import_path.split("::")
        return parts[0] in std_crates

    def extract_functions(self, ast_root: Any) -> List[Function]:
        """Extract function definitions from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.functions or []
        return []

    def extract_classes(self, ast_root: Any) -> List[Class]:
        """Extract class definitions from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.classes or []
        return []

    def extract_imports(self, ast_root: Any) -> List[Import]:
        """Extract import statements from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.imports or []
        return []

    def extract_variables(self, ast_root: Any) -> List[Variable]:
        """Extract variable definitions from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.variables or []
        return []
