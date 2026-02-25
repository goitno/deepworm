"""Template engine for document generation.

Supports variable interpolation, conditionals, loops, filters,
template inheritance (extends/block), includes, and macros.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence


class TemplateError(Exception):
    """Raised when template parsing or rendering fails."""


class TokenType(Enum):
    """Types of template tokens."""

    TEXT = "text"
    VARIABLE = "variable"
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    ENDIF = "endif"
    FOR = "for"
    ENDFOR = "endfor"
    BLOCK = "block"
    ENDBLOCK = "endblock"
    EXTENDS = "extends"
    INCLUDE = "include"
    MACRO = "macro"
    ENDMACRO = "endmacro"
    CALL_MACRO = "call_macro"
    COMMENT = "comment"
    RAW = "raw"


@dataclass
class Token:
    """A parsed template token."""

    token_type: TokenType
    value: str
    line: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.token_type.value,
            "value": self.value,
            "line": self.line,
        }


@dataclass
class TemplateContext:
    """Variables and state for template rendering."""

    variables: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Callable] = field(default_factory=dict)
    macros: Dict[str, "MacroDef"] = field(default_factory=dict)
    parent: Optional["TemplateContext"] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable, supporting dot notation (e.g. 'user.name')."""
        parts = key.split(".")
        value = self.variables.get(parts[0])
        if value is None and self.parent:
            value = self.parent.get(parts[0])
        if value is None:
            return default
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def child(self) -> "TemplateContext":
        """Create a child context inheriting filters and macros."""
        ctx = TemplateContext(
            variables=dict(self.variables),
            filters=dict(self.filters),
            macros=dict(self.macros),
            parent=self,
        )
        return ctx

    def apply_filter(self, name: str, value: Any, *args: Any) -> Any:
        """Apply a named filter to a value."""
        if name in self.filters:
            return self.filters[name](value, *args)
        builtin = _BUILTIN_FILTERS.get(name)
        if builtin:
            return builtin(value, *args)
        raise TemplateError(f"Unknown filter: {name}")


@dataclass
class MacroDef:
    """A reusable template macro definition."""

    name: str
    params: List[str]
    body: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "params": self.params, "body": self.body}


@dataclass
class RenderResult:
    """Result of template rendering."""

    output: str
    variables_used: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output": self.output,
            "variables_used": self.variables_used,
            "errors": self.errors,
            "success": self.success,
        }


# ---------------------------------------------------------------------------
# Built-in filters
# ---------------------------------------------------------------------------

def _filter_upper(value: Any, *_args: Any) -> str:
    return str(value).upper()


def _filter_lower(value: Any, *_args: Any) -> str:
    return str(value).lower()


def _filter_title(value: Any, *_args: Any) -> str:
    return str(value).title()


def _filter_strip(value: Any, *_args: Any) -> str:
    return str(value).strip()


def _filter_default(value: Any, *args: Any) -> Any:
    if value is None or value == "":
        return args[0] if args else ""
    return value


def _filter_length(value: Any, *_args: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def _filter_join(value: Any, *args: Any) -> str:
    sep = args[0] if args else ", "
    if isinstance(value, (list, tuple)):
        return str(sep).join(str(v) for v in value)
    return str(value)


def _filter_replace(value: Any, *args: Any) -> str:
    if len(args) >= 2:
        return str(value).replace(str(args[0]), str(args[1]))
    return str(value)


def _filter_truncate(value: Any, *args: Any) -> str:
    s = str(value)
    max_len = int(args[0]) if args else 50
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _filter_first(value: Any, *_args: Any) -> Any:
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _filter_last(value: Any, *_args: Any) -> Any:
    if isinstance(value, (list, tuple)) and value:
        return value[-1]
    return value


def _filter_reverse(value: Any, *_args: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return list(reversed(value))
    return str(value)[::-1]


def _filter_sort(value: Any, *_args: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return sorted(value)
    return value


def _filter_unique(value: Any, *_args: Any) -> Any:
    if isinstance(value, (list, tuple)):
        seen: set = set()
        result = []
        for v in value:
            key = str(v)
            if key not in seen:
                seen.add(key)
                result.append(v)
        return result
    return value


def _filter_capitalize(value: Any, *_args: Any) -> str:
    return str(value).capitalize()


def _filter_wordcount(value: Any, *_args: Any) -> int:
    return len(str(value).split())


_BUILTIN_FILTERS: Dict[str, Callable] = {
    "upper": _filter_upper,
    "lower": _filter_lower,
    "title": _filter_title,
    "strip": _filter_strip,
    "default": _filter_default,
    "length": _filter_length,
    "join": _filter_join,
    "replace": _filter_replace,
    "truncate": _filter_truncate,
    "first": _filter_first,
    "last": _filter_last,
    "reverse": _filter_reverse,
    "sort": _filter_sort,
    "unique": _filter_unique,
    "capitalize": _filter_capitalize,
    "wordcount": _filter_wordcount,
}


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(
    r"\{%[-\s]*(.*?)[-\s]*%\}"   # {% tag %}
    r"|\{\{(.*?)\}\}"             # {{ variable }}
    r"|\{#(.*?)#\}",              # {# comment #}
    re.DOTALL,
)


def _tokenize(template: str) -> List[Token]:
    """Parse template string into tokens."""
    tokens: List[Token] = []
    pos = 0
    line = 1

    for m in _TAG_RE.finditer(template):
        start = m.start()
        # Text before this tag
        if start > pos:
            text = template[pos:start]
            tokens.append(Token(TokenType.TEXT, text, line))
            line += text.count("\n")

        tag_content = m.group(1)  # {% ... %}
        var_content = m.group(2)  # {{ ... }}
        comment = m.group(3)      # {# ... #}

        if comment is not None:
            tokens.append(Token(TokenType.COMMENT, comment.strip(), line))
        elif var_content is not None:
            tokens.append(Token(TokenType.VARIABLE, var_content.strip(), line))
        elif tag_content is not None:
            tag = tag_content.strip()
            if tag.startswith("if "):
                tokens.append(Token(TokenType.IF, tag[3:].strip(), line))
            elif tag.startswith("elif "):
                tokens.append(Token(TokenType.ELIF, tag[5:].strip(), line))
            elif tag == "else":
                tokens.append(Token(TokenType.ELSE, "", line))
            elif tag == "endif":
                tokens.append(Token(TokenType.ENDIF, "", line))
            elif tag.startswith("for "):
                tokens.append(Token(TokenType.FOR, tag[4:].strip(), line))
            elif tag == "endfor":
                tokens.append(Token(TokenType.ENDFOR, "", line))
            elif tag.startswith("block "):
                tokens.append(Token(TokenType.BLOCK, tag[6:].strip(), line))
            elif tag == "endblock":
                tokens.append(Token(TokenType.ENDBLOCK, "", line))
            elif tag.startswith("extends "):
                name = tag[8:].strip().strip("'\"")
                tokens.append(Token(TokenType.EXTENDS, name, line))
            elif tag.startswith("include "):
                name = tag[8:].strip().strip("'\"")
                tokens.append(Token(TokenType.INCLUDE, name, line))
            elif tag.startswith("macro "):
                tokens.append(Token(TokenType.MACRO, tag[6:].strip(), line))
            elif tag == "endmacro":
                tokens.append(Token(TokenType.ENDMACRO, "", line))
            elif tag.startswith("call "):
                tokens.append(Token(TokenType.CALL_MACRO, tag[5:].strip(), line))
            elif tag == "raw":
                tokens.append(Token(TokenType.RAW, "", line))
            else:
                tokens.append(Token(TokenType.TEXT, m.group(0), line))

        matched_text = m.group(0)
        line += matched_text.count("\n")
        pos = m.end()

    # Remaining text
    if pos < len(template):
        tokens.append(Token(TokenType.TEXT, template[pos:], line))

    return tokens


# ---------------------------------------------------------------------------
# Expression evaluator
# ---------------------------------------------------------------------------

def _eval_expr(expr: str, ctx: TemplateContext) -> Any:
    """Evaluate a simple expression with filters.

    Supports:
      - Variable lookup with dot notation
      - String literals ('...', "...")
      - Integer and float literals
      - Pipe filters: value | filter_name
      - Filter arguments: value | filter_name:"arg"
      - Boolean operators: and, or, not
      - Comparisons: ==, !=, <, >, <=, >=
      - Truthiness check
    """
    expr = expr.strip()

    # Handle pipe filters first
    if "|" in expr:
        parts = expr.split("|")
        value = _eval_expr(parts[0], ctx)
        for f in parts[1:]:
            f = f.strip()
            # Check for filter arguments: filter_name:"arg1","arg2"
            filter_match = re.match(r"(\w+)\s*:\s*(.*)", f)
            if filter_match:
                filter_name = filter_match.group(1)
                args_str = filter_match.group(2)
                # Parse arguments
                filter_args = []
                for arg in re.findall(r'"([^"]*)"' + r"|'([^']*)'|(\d+(?:\.\d+)?)", args_str):
                    val = arg[0] or arg[1] or arg[2]
                    # Try to convert to number
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            pass
                    filter_args.append(val)
                value = ctx.apply_filter(filter_name, value, *filter_args)
            else:
                value = ctx.apply_filter(f, value)
        return value

    # Comparison operators
    for op in ("==", "!=", "<=", ">=", "<", ">"):
        if op in expr:
            idx = expr.index(op)
            left = _eval_expr(expr[:idx], ctx)
            right = _eval_expr(expr[idx + len(op):], ctx)
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == "<=":
                return left <= right
            elif op == ">=":
                return left >= right
            elif op == "<":
                return left < right
            elif op == ">":
                return left > right

    # Boolean operators
    if " and " in expr:
        parts = expr.split(" and ", 1)
        return _eval_expr(parts[0], ctx) and _eval_expr(parts[1], ctx)
    if " or " in expr:
        parts = expr.split(" or ", 1)
        return _eval_expr(parts[0], ctx) or _eval_expr(parts[1], ctx)
    if expr.startswith("not "):
        return not _eval_expr(expr[4:], ctx)

    # String literal
    if (expr.startswith('"') and expr.endswith('"')) or \
       (expr.startswith("'") and expr.endswith("'")):
        return expr[1:-1]

    # Numeric literal
    try:
        if "." in expr:
            return float(expr)
        return int(expr)
    except ValueError:
        pass

    # Boolean literals
    if expr == "true" or expr == "True":
        return True
    if expr == "false" or expr == "False":
        return False
    if expr == "none" or expr == "None":
        return None

    # Variable lookup
    return ctx.get(expr)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _render_tokens(
    tokens: List[Token],
    ctx: TemplateContext,
    templates: Optional[Dict[str, str]] = None,
) -> tuple:
    """Render tokens into output string. Returns (output, variables_used, errors)."""
    output_parts: List[str] = []
    vars_used: List[str] = []
    errors: List[str] = []
    i = 0
    templates = templates or {}

    while i < len(tokens):
        tok = tokens[i]

        if tok.token_type == TokenType.TEXT:
            output_parts.append(tok.value)
            i += 1

        elif tok.token_type == TokenType.COMMENT:
            i += 1  # skip comments

        elif tok.token_type == TokenType.VARIABLE:
            expr = tok.value
            var_name = expr.split("|")[0].split(".")[0].strip()
            if var_name not in vars_used:
                vars_used.append(var_name)
            try:
                value = _eval_expr(expr, ctx)
                output_parts.append(str(value) if value is not None else "")
            except TemplateError as e:
                errors.append(str(e))
                output_parts.append("")
            i += 1

        elif tok.token_type == TokenType.IF:
            # Collect if/elif/else/endif blocks
            condition = tok.value
            blocks: List[tuple] = []  # (condition_expr, token_list)
            current_tokens: List[Token] = []
            depth = 1
            i += 1
            while i < len(tokens) and depth > 0:
                t = tokens[i]
                if t.token_type == TokenType.IF:
                    depth += 1
                    current_tokens.append(t)
                elif t.token_type == TokenType.ENDIF:
                    depth -= 1
                    if depth == 0:
                        blocks.append((condition, current_tokens))
                    else:
                        current_tokens.append(t)
                elif t.token_type == TokenType.ELIF and depth == 1:
                    blocks.append((condition, current_tokens))
                    condition = t.value
                    current_tokens = []
                elif t.token_type == TokenType.ELSE and depth == 1:
                    blocks.append((condition, current_tokens))
                    condition = None  # else branch
                    current_tokens = []
                else:
                    current_tokens.append(t)
                i += 1

            # Evaluate conditions
            rendered = False
            for cond, block_tokens in blocks:
                if cond is None:
                    # else block
                    if not rendered:
                        out, vu, errs = _render_tokens(block_tokens, ctx, templates)
                        output_parts.append(out)
                        vars_used.extend(vu)
                        errors.extend(errs)
                    break
                else:
                    if _eval_expr(cond, ctx):
                        out, vu, errs = _render_tokens(block_tokens, ctx, templates)
                        output_parts.append(out)
                        vars_used.extend(vu)
                        errors.extend(errs)
                        rendered = True
                        break

        elif tok.token_type == TokenType.FOR:
            # Parse: "item in items"
            for_match = re.match(r"(\w+)\s+in\s+(.*)", tok.value)
            if not for_match:
                errors.append(f"Invalid for syntax: {tok.value}")
                i += 1
                continue
            loop_var = for_match.group(1)
            iterable_expr = for_match.group(2).strip()
            var_name = iterable_expr.split(".")[0].strip()
            if var_name not in vars_used:
                vars_used.append(var_name)

            # Collect body tokens
            body_tokens: List[Token] = []
            depth = 1
            i += 1
            while i < len(tokens) and depth > 0:
                t = tokens[i]
                if t.token_type == TokenType.FOR:
                    depth += 1
                    body_tokens.append(t)
                elif t.token_type == TokenType.ENDFOR:
                    depth -= 1
                    if depth > 0:
                        body_tokens.append(t)
                else:
                    body_tokens.append(t)
                i += 1

            # Iterate
            iterable = _eval_expr(iterable_expr, ctx)
            if iterable and hasattr(iterable, "__iter__"):
                items = list(iterable)
                for idx, item in enumerate(items):
                    child_ctx = ctx.child()
                    child_ctx.set(loop_var, item)
                    child_ctx.set("loop", {
                        "index": idx + 1,
                        "index0": idx,
                        "first": idx == 0,
                        "last": idx == len(items) - 1,
                        "length": len(items),
                    })
                    out, vu, errs = _render_tokens(body_tokens, child_ctx, templates)
                    output_parts.append(out)
                    vars_used.extend(vu)
                    errors.extend(errs)

        elif tok.token_type == TokenType.INCLUDE:
            tpl_name = tok.value
            if tpl_name in templates:
                included = render_template(templates[tpl_name], ctx.variables, ctx.filters, templates)
                output_parts.append(included.output)
                vars_used.extend(included.variables_used)
                errors.extend(included.errors)
            else:
                errors.append(f"Template not found: {tpl_name}")
            i += 1

        elif tok.token_type == TokenType.MACRO:
            # Parse: "name(param1, param2)"
            macro_match = re.match(r"(\w+)\s*\((.*?)\)", tok.value)
            if not macro_match:
                errors.append(f"Invalid macro syntax: {tok.value}")
                i += 1
                continue
            macro_name = macro_match.group(1)
            params = [p.strip() for p in macro_match.group(2).split(",") if p.strip()]

            # Collect body
            body_parts: List[str] = []
            i += 1
            depth = 1
            while i < len(tokens) and depth > 0:
                t = tokens[i]
                if t.token_type == TokenType.MACRO:
                    depth += 1
                    body_parts.append(t.value)
                elif t.token_type == TokenType.ENDMACRO:
                    depth -= 1
                    if depth > 0:
                        body_parts.append("")
                else:
                    if t.token_type == TokenType.TEXT:
                        body_parts.append(t.value)
                    elif t.token_type == TokenType.VARIABLE:
                        body_parts.append("{{ " + t.value + " }}")
                    else:
                        # Reconstruct tag
                        body_parts.append(t.value)
                i += 1

            ctx.macros[macro_name] = MacroDef(
                name=macro_name,
                params=params,
                body="".join(body_parts),
            )

        elif tok.token_type == TokenType.CALL_MACRO:
            # Parse: "name(arg1, arg2)"
            call_match = re.match(r"(\w+)\s*\((.*?)\)", tok.value)
            if not call_match:
                errors.append(f"Invalid macro call: {tok.value}")
                i += 1
                continue
            macro_name = call_match.group(1)
            args_str = call_match.group(2)
            args = [a.strip() for a in args_str.split(",") if a.strip()] if args_str.strip() else []

            macro = ctx.macros.get(macro_name)
            if not macro:
                errors.append(f"Undefined macro: {macro_name}")
                i += 1
                continue

            child_ctx = ctx.child()
            for pi, param in enumerate(macro.params):
                if pi < len(args):
                    child_ctx.set(param, _eval_expr(args[pi], ctx))
                else:
                    child_ctx.set(param, None)
            result = render_template(macro.body, child_ctx.variables, child_ctx.filters, templates)
            output_parts.append(result.output)
            vars_used.extend(result.variables_used)
            errors.extend(result.errors)
            i += 1

        elif tok.token_type == TokenType.RAW:
            # Collect raw text until {% endraw %}
            i += 1
            raw_parts: List[str] = []
            while i < len(tokens):
                t = tokens[i]
                if t.token_type == TokenType.TEXT and "{% endraw %}" in t.value:
                    before, _, after = t.value.partition("{% endraw %}")
                    raw_parts.append(before)
                    if after:
                        tokens.insert(i + 1, Token(TokenType.TEXT, after, t.line))
                    i += 1
                    break
                elif t.token_type == TokenType.TEXT:
                    raw_parts.append(t.value)
                else:
                    # Reconstruct the original tag text
                    if t.token_type == TokenType.VARIABLE:
                        raw_parts.append("{{ " + t.value + " }}")
                    else:
                        raw_parts.append(t.value)
                i += 1
            output_parts.append("".join(raw_parts))

        elif tok.token_type == TokenType.EXTENDS:
            # Template inheritance: find parent, render blocks
            parent_name = tok.value
            if parent_name not in templates:
                errors.append(f"Parent template not found: {parent_name}")
                i += 1
                continue

            # Collect block definitions from child
            child_blocks: Dict[str, List[Token]] = {}
            i += 1
            while i < len(tokens):
                t = tokens[i]
                if t.token_type == TokenType.BLOCK:
                    block_name = t.value
                    block_tokens_list: List[Token] = []
                    i += 1
                    depth = 1
                    while i < len(tokens) and depth > 0:
                        bt = tokens[i]
                        if bt.token_type == TokenType.BLOCK:
                            depth += 1
                            block_tokens_list.append(bt)
                        elif bt.token_type == TokenType.ENDBLOCK:
                            depth -= 1
                            if depth > 0:
                                block_tokens_list.append(bt)
                        else:
                            block_tokens_list.append(bt)
                        i += 1
                    child_blocks[block_name] = block_tokens_list
                else:
                    i += 1

            # Render parent template, substituting blocks
            parent_tokens = _tokenize(templates[parent_name])
            # Replace block content in parent with child blocks
            resolved_tokens: List[Token] = []
            pi = 0
            while pi < len(parent_tokens):
                pt = parent_tokens[pi]
                if pt.token_type == TokenType.BLOCK:
                    block_name = pt.value
                    # Skip parent block content
                    parent_block: List[Token] = []
                    pi += 1
                    depth = 1
                    while pi < len(parent_tokens) and depth > 0:
                        pbt = parent_tokens[pi]
                        if pbt.token_type == TokenType.BLOCK:
                            depth += 1
                            parent_block.append(pbt)
                        elif pbt.token_type == TokenType.ENDBLOCK:
                            depth -= 1
                            if depth > 0:
                                parent_block.append(pbt)
                        else:
                            parent_block.append(pbt)
                        pi += 1
                    # Use child block if available, otherwise parent
                    if block_name in child_blocks:
                        resolved_tokens.extend(child_blocks[block_name])
                    else:
                        resolved_tokens.extend(parent_block)
                else:
                    resolved_tokens.append(pt)
                    pi += 1

            out, vu, errs = _render_tokens(resolved_tokens, ctx, templates)
            output_parts.append(out)
            vars_used.extend(vu)
            errors.extend(errs)

        else:
            i += 1

    return "".join(output_parts), vars_used, errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_template(
    template: str,
    variables: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Callable]] = None,
    templates: Optional[Dict[str, str]] = None,
) -> RenderResult:
    """Render a template string with given variables.

    Args:
        template: Template string with {{ vars }}, {% tags %}, {# comments #}.
        variables: Dictionary of template variables.
        filters: Custom filter functions.
        templates: Named templates for include/extends.

    Returns:
        RenderResult with output text, used variables, and any errors.
    """
    ctx = TemplateContext(
        variables=dict(variables or {}),
        filters=dict(filters or {}),
    )
    tokens = _tokenize(template)
    output, vars_used, errors = _render_tokens(tokens, ctx, templates)
    unique_vars = list(dict.fromkeys(vars_used))
    return RenderResult(output=output, variables_used=unique_vars, errors=errors)


def validate_template(template: str) -> List[str]:
    """Validate a template string and return a list of issues.

    Checks for:
      - Unclosed tags (if/for/block/macro)
      - Unknown tag syntax
      - Empty variable expressions
    """
    issues: List[str] = []
    tokens = _tokenize(template)
    stack: List[tuple] = []

    for tok in tokens:
        if tok.token_type == TokenType.IF:
            stack.append(("if", tok.line))
        elif tok.token_type == TokenType.FOR:
            stack.append(("for", tok.line))
        elif tok.token_type == TokenType.BLOCK:
            stack.append(("block", tok.line))
        elif tok.token_type == TokenType.MACRO:
            stack.append(("macro", tok.line))
        elif tok.token_type == TokenType.ENDIF:
            if not stack or stack[-1][0] != "if":
                issues.append(f"Line {tok.line}: Unexpected endif")
            else:
                stack.pop()
        elif tok.token_type == TokenType.ENDFOR:
            if not stack or stack[-1][0] != "for":
                issues.append(f"Line {tok.line}: Unexpected endfor")
            else:
                stack.pop()
        elif tok.token_type == TokenType.ENDBLOCK:
            if not stack or stack[-1][0] != "block":
                issues.append(f"Line {tok.line}: Unexpected endblock")
            else:
                stack.pop()
        elif tok.token_type == TokenType.ENDMACRO:
            if not stack or stack[-1][0] != "macro":
                issues.append(f"Line {tok.line}: Unexpected endmacro")
            else:
                stack.pop()
        elif tok.token_type == TokenType.VARIABLE:
            if not tok.value.strip():
                issues.append(f"Line {tok.line}: Empty variable expression")

    for tag, line in stack:
        issues.append(f"Line {line}: Unclosed {tag}")

    return issues


def extract_variables(template: str) -> List[str]:
    """Extract all variable names used in a template."""
    tokens = _tokenize(template)
    variables: List[str] = []
    for tok in tokens:
        if tok.token_type == TokenType.VARIABLE:
            var_name = tok.value.split("|")[0].split(".")[0].strip()
            if var_name and var_name not in variables:
                variables.append(var_name)
        elif tok.token_type in (TokenType.IF, TokenType.ELIF):
            # Extract variables from conditions
            expr = tok.value
            for word in re.findall(r"\b([a-zA-Z_]\w*)\b", expr):
                if word not in ("and", "or", "not", "true", "false", "none",
                                "True", "False", "None", "in"):
                    if word not in variables:
                        variables.append(word)
        elif tok.token_type == TokenType.FOR:
            # Extract iterable variable
            for_match = re.match(r"\w+\s+in\s+(\w+)", tok.value)
            if for_match:
                var_name = for_match.group(1)
                if var_name not in variables:
                    variables.append(var_name)
    return variables


def list_filters() -> List[str]:
    """Return names of all built-in filters."""
    return sorted(_BUILTIN_FILTERS.keys())


def create_context(
    variables: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Callable]] = None,
) -> TemplateContext:
    """Create a reusable template context."""
    return TemplateContext(
        variables=dict(variables or {}),
        filters=dict(filters or {}),
    )


# ---------------------------------------------------------------------------
# Preset templates
# ---------------------------------------------------------------------------

def report_template() -> str:
    """Return a standard research report template."""
    return """# {{ title }}

{% if author %}*By {{ author }}*{% endif %}
{% if date %}*{{ date }}*{% endif %}

## Summary

{{ summary }}

{% for section in sections %}
## {{ section.heading }}

{{ section.content }}

{% endfor %}
{% if references %}
## References

{% for ref in references %}
{{ loop.index }}. {{ ref }}
{% endfor %}
{% endif %}"""


def comparison_template() -> str:
    """Return a comparison report template."""
    return """# {{ title | default:"Comparison" }}

| Feature | {% for item in items %}{{ item.name }} | {% endfor %}
|---------|{% for item in items %}---------|{% endfor %}
{% for feature in features %}| {{ feature.name }} | {% for item in items %}{{ feature.values | default:"N/A" }} | {% endfor %}
{% endfor %}

{% if conclusion %}
## Conclusion

{{ conclusion }}
{% endif %}"""
