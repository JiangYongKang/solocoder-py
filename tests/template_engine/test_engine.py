import pytest

from solocoder_py.template_engine import (
    InvalidConditionError,
    InvalidLoopError,
    TemplateEngine,
    TemplateSyntaxError,
    UnclosedTagError,
    VariableNotFoundError,
    render_template,
)


class TestVariableInterpolation:
    def test_simple_variable(self):
        result = render_template("Hello, {{ name }}!", {"name": "World"})
        assert result == "Hello, World!"

    def test_multiple_variables(self):
        result = render_template(
            "{{ first }} {{ last }}",
            {"first": "John", "last": "Doe"},
        )
        assert result == "John Doe"

    def test_nested_dict_access(self):
        result = render_template(
            "User: {{ user.name }}, Age: {{ user.age }}",
            {"user": {"name": "Alice", "age": 30}},
        )
        assert result == "User: Alice, Age: 30"

    def test_deeply_nested_access(self):
        result = render_template(
            "{{ a.b.c.d }}",
            {"a": {"b": {"c": {"d": "deep_value"}}}},
        )
        assert result == "deep_value"

    def test_numeric_variable(self):
        result = render_template("Count: {{ count }}", {"count": 42})
        assert result == "Count: 42"

    def test_float_variable(self):
        result = render_template("Price: {{ price }}", {"price": 3.14})
        assert result == "Price: 3.14"

    def test_boolean_variable(self):
        result = render_template("Active: {{ active }}", {"active": True})
        assert result == "Active: True"

    def test_none_variable(self):
        result = render_template("Value: {{ val }}", {"val": None})
        assert result == "Value: "

    def test_variable_with_extra_spaces(self):
        result = render_template("{{   name   }}", {"name": "test"})
        assert result == "test"

    def test_object_attribute_access(self):
        class User:
            def __init__(self, name, email):
                self.name = name
                self.email = email

        user = User("Bob", "bob@example.com")
        result = render_template("{{ u.name }} <{{ u.email }}>", {"u": user})
        assert result == "Bob <bob@example.com>"

    def test_mixed_dict_and_object_access(self):
        class Profile:
            def __init__(self, bio):
                self.bio = bio

        ctx = {"user": {"profile": Profile("Hello World")}}
        result = render_template("{{ user.profile.bio }}", ctx)
        assert result == "Hello World"


class TestUndefinedVariables:
    def test_undefined_variable_default_empty(self):
        result = render_template("Hello, {{ name }}!", {})
        assert result == "Hello, !"

    def test_undefined_variable_custom_placeholder(self):
        result = render_template(
            "Hello, {{ name }}!",
            {},
            undefined_placeholder="[MISSING]",
        )
        assert result == "Hello, [MISSING]!"

    def test_undefined_nested_variable(self):
        result = render_template("{{ user.name }}", {"user": {}})
        assert result == ""

    def test_undefined_deeply_nested_variable(self):
        result = render_template("{{ a.b.c }}", {"a": {}})
        assert result == ""

    def test_undefined_with_custom_placeholder_nested(self):
        result = render_template(
            "{{ user.address.city }}",
            {"user": {}},
            undefined_placeholder="N/A",
        )
        assert result == "N/A"

    def test_strict_mode_raises(self):
        engine = TemplateEngine(strict=True)
        with pytest.raises(VariableNotFoundError, match="Variable not found"):
            engine.render("{{ name }}", {})

    def test_strict_mode_nested_raises(self):
        engine = TemplateEngine(strict=True)
        with pytest.raises(VariableNotFoundError, match="Variable not found"):
            engine.render("{{ user.name }}", {"user": {}})

    def test_undefined_in_condition(self):
        result = render_template(
            "{% if undefined_var %}yes{% else %}no{% endif %}",
            {},
        )
        assert result == "no"


class TestConditionalBlocks:
    def test_if_true(self):
        result = render_template(
            "{% if active %}Enabled{% endif %}",
            {"active": True},
        )
        assert result == "Enabled"

    def test_if_false(self):
        result = render_template(
            "{% if active %}Enabled{% endif %}",
            {"active": False},
        )
        assert result == ""

    def test_if_else_true(self):
        result = render_template(
            "{% if active %}Yes{% else %}No{% endif %}",
            {"active": True},
        )
        assert result == "Yes"

    def test_if_else_false(self):
        result = render_template(
            "{% if active %}Yes{% else %}No{% endif %}",
            {"active": False},
        )
        assert result == "No"

    def test_truthy_values(self):
        for val in [1, "hello", [1], {"a": 1}]:
            result = render_template(
                "{% if val %}T{% else %}F{% endif %}",
                {"val": val},
            )
            assert result == "T", f"Failed for value: {val}"

    def test_falsy_values(self):
        for val in [0, "", [], {}, None]:
            result = render_template(
                "{% if val %}T{% else %}F{% endif %}",
                {"val": val},
            )
            assert result == "F", f"Failed for value: {val}"

    def test_equality_comparison_strings(self):
        result = render_template(
            "{% if role == 'admin' %}Admin{% else %}User{% endif %}",
            {"role": "admin"},
        )
        assert result == "Admin"

    def test_equality_comparison_strings_false(self):
        result = render_template(
            "{% if role == 'admin' %}Admin{% else %}User{% endif %}",
            {"role": "user"},
        )
        assert result == "User"

    def test_equality_comparison_double_quotes(self):
        result = render_template(
            '{% if status == "done" %}Complete{% else %}Pending{% endif %}',
            {"status": "done"},
        )
        assert result == "Complete"

    def test_equality_comparison_numbers(self):
        result = render_template(
            "{% if count == 5 %}Five{% else %}Not five{% endif %}",
            {"count": 5},
        )
        assert result == "Five"

    def test_equality_comparison_variable_to_variable(self):
        result = render_template(
            "{% if a == b %}Equal{% else %}Not equal{% endif %}",
            {"a": 10, "b": 10},
        )
        assert result == "Equal"

    def test_not_equal_comparison(self):
        result = render_template(
            "{% if status != 'error' %}OK{% else %}Error{% endif %}",
            {"status": "success"},
        )
        assert result == "OK"

    def test_not_equal_comparison_false(self):
        result = render_template(
            "{% if status != 'error' %}OK{% else %}Error{% endif %}",
            {"status": "error"},
        )
        assert result == "Error"

    def test_nested_if_blocks(self):
        result = render_template(
            "{% if a %}{% if b %}Both{% else %}Only A{% endif %}{% else %}Neither{% endif %}",
            {"a": True, "b": True},
        )
        assert result == "Both"

    def test_nested_if_outer_true_inner_false(self):
        result = render_template(
            "{% if a %}{% if b %}Both{% else %}Only A{% endif %}{% else %}Neither{% endif %}",
            {"a": True, "b": False},
        )
        assert result == "Only A"

    def test_nested_if_outer_false(self):
        result = render_template(
            "{% if a %}{% if b %}Both{% else %}Only A{% endif %}{% else %}Neither{% endif %}",
            {"a": False, "b": True},
        )
        assert result == "Neither"

    def test_if_with_variable_interpolation(self):
        result = render_template(
            "{% if show %}Hello, {{ name }}!{% endif %}",
            {"show": True, "name": "Alice"},
        )
        assert result == "Hello, Alice!"

    def test_else_with_variable_interpolation(self):
        result = render_template(
            "{% if show %}Hello{% else %}Goodbye, {{ name }}!{% endif %}",
            {"show": False, "name": "Bob"},
        )
        assert result == "Goodbye, Bob!"

    def test_boolean_literal_true(self):
        result = render_template("{% if true %}Yes{% else %}No{% endif %}", {})
        assert result == "Yes"

    def test_boolean_literal_false(self):
        result = render_template("{% if false %}Yes{% else %}No{% endif %}", {})
        assert result == "No"


class TestLoopBlocks:
    def test_simple_loop(self):
        result = render_template(
            "{% for item in items %}{{ item }},{% endfor %}",
            {"items": ["a", "b", "c"]},
        )
        assert result == "a,b,c,"

    def test_loop_with_object_items(self):
        result = render_template(
            "{% for user in users %}{{ user.name }}:{{ user.age }};{% endfor %}",
            {"users": [{"name": "A", "age": 1}, {"name": "B", "age": 2}]},
        )
        assert result == "A:1;B:2;"

    def test_loop_index(self):
        result = render_template(
            "{% for x in items %}{{ loop.index }},{% endfor %}",
            {"items": ["a", "b", "c"]},
        )
        assert result == "1,2,3,"

    def test_loop_index0(self):
        result = render_template(
            "{% for x in items %}{{ loop.index0 }},{% endfor %}",
            {"items": ["a", "b", "c"]},
        )
        assert result == "0,1,2,"

    def test_loop_first(self):
        result = render_template(
            "{% for x in items %}{% if loop.first %}[{{ x }}]{% else %}{{ x }}{% endif %} {% endfor %}",
            {"items": ["a", "b", "c"]},
        )
        assert result == "[a] b c "

    def test_loop_with_item_and_index(self):
        result = render_template(
            "{% for n in nums %}{{ loop.index }}:{{ n }}\n{% endfor %}",
            {"nums": [10, 20, 30]},
        )
        assert result == "1:10\n2:20\n3:30\n"

    def test_empty_loop(self):
        result = render_template(
            "{% for item in items %}{{ item }}{% endfor %}",
            {"items": []},
        )
        assert result == ""

    def test_nested_loops(self):
        result = render_template(
            "{% for row in rows %}{% for col in row %}{{ col }}{% endfor %};{% endfor %}",
            {"rows": [[1, 2], [3, 4]]},
        )
        assert result == "12;34;"

    def test_deeply_nested_loops(self):
        data = {"levels": [[[1, 2], [3, 4]], [[5, 6]]]}
        result = render_template(
            "{% for l1 in levels %}{% for l2 in l1 %}{% for l3 in l2 %}{{ l3 }}{% endfor %}{% endfor %}{% endfor %}",
            data,
        )
        assert result == "123456"

    def test_loop_with_conditional(self):
        result = render_template(
            "{% for n in nums %}{% if n > 2 %}{{ n }}{% endif %}{% endfor %}",
            {"nums": [1, 2, 3, 4, 5]},
        )
        assert result == "345"

    def test_loop_last(self):
        result = render_template(
            "{% for n in nums %}{{ n }}{% if not loop.last %},{% endif %}{% endfor %}",
            {"nums": [1, 2, 3]},
        )
        assert result == "1,2,3"


class TestBoundaryConditions:
    def test_empty_template(self):
        result = render_template("", {})
        assert result == ""

    def test_empty_context(self):
        result = render_template("Hello World", {})
        assert result == "Hello World"

    def test_template_with_only_text(self):
        result = render_template("Just plain text", {"var": "value"})
        assert result == "Just plain text"

    def test_multiple_spaces_in_tags(self):
        result = render_template(
            "{{   name   }} and {%   if   active   %}Yes{%   endif   %}",
            {"name": "test", "active": True},
        )
        assert result == "test and Yes"

    def test_variable_at_beginning(self):
        result = render_template("{{ name }} World", {"name": "Hello"})
        assert result == "Hello World"

    def test_variable_at_end(self):
        result = render_template("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_consecutive_variables(self):
        result = render_template("{{ a }}{{ b }}{{ c }}", {"a": "1", "b": "2", "c": "3"})
        assert result == "123"

    def test_large_template(self):
        parts = ["{{ var }}"] * 100
        template = "".join(parts)
        result = render_template(template, {"var": "x"})
        assert result == "x" * 100

    def test_large_list_in_loop(self):
        items = list(range(100))
        result = render_template(
            "{% for i in items %}{{ i }},{% endfor %}",
            {"items": items},
        )
        assert result == ",".join(str(i) for i in items) + ","

    def test_newlines_preserved(self):
        result = render_template("Line 1\n{{ var }}\nLine 3", {"var": "Line 2"})
        assert result == "Line 1\nLine 2\nLine 3"

    def test_whitespace_preserved(self):
        result = render_template("  {{ var }}  ", {"var": "x"})
        assert result == "  x  "


class TestComplexIntegration:
    def test_if_inside_loop(self):
        template = "{% for u in users %}{% if u.active %}{{ u.name }} {% endif %}{% endfor %}"
        ctx = {
            "users": [
                {"name": "A", "active": True},
                {"name": "B", "active": False},
                {"name": "C", "active": True},
            ]
        }
        result = render_template(template, ctx)
        assert result == "A C "

    def test_loop_inside_if(self):
        template = "{% if show %}{% for n in nums %}{{ n }}{% endfor %}{% else %}none{% endif %}"
        result = render_template(template, {"show": True, "nums": [1, 2, 3]})
        assert result == "123"
        result = render_template(template, {"show": False, "nums": [1, 2, 3]})
        assert result == "none"

    def test_variable_in_condition_inside_loop(self):
        template = "{% for item in items %}{% if item == target %}FOUND{% endif %}{% endfor %}"
        result = render_template(template, {"items": [1, 2, 3, 4], "target": 3})
        assert result == "FOUND"

    def test_nested_variables_in_conditions(self):
        template = "{% if user.profile.active %}{{ user.name }}{% else %}inactive{% endif %}"
        ctx = {"user": {"name": "Bob", "profile": {"active": True}}}
        result = render_template(template, ctx)
        assert result == "Bob"

    def test_deeply_nested_mixed_structure(self):
        template = """{% if data %}
{% for section in data.sections %}
## {{ section.title }}
{% if section.items %}{% for item in section.items %}- {{ item.name }}{% if item.desc %}: {{ item.desc }}{% endif %}
{% endfor %}{% endif %}
{% endfor %}
{% else %}No data{% endif %}"""
        ctx = {
            "data": {
                "sections": [
                    {
                        "title": "Fruits",
                        "items": [
                            {"name": "Apple", "desc": "Red fruit"},
                            {"name": "Banana"},
                        ],
                    },
                    {"title": "Empty", "items": []},
                ]
            }
        }
        result = render_template(template, ctx)
        assert "## Fruits" in result
        assert "- Apple: Red fruit" in result
        assert "- Banana" in result
        assert "## Empty" in result

    def test_multiline_condition(self):
        template = """{% if
user.active
%}Active{% else %}Inactive{% endif %}"""
        result = render_template(template, {"user": {"active": True}})
        assert result == "Active"


class TestErrorConditions:
    def test_unclosed_if_tag(self):
        with pytest.raises(UnclosedTagError, match="Unclosed.*if"):
            render_template("{% if true %}Hello", {})

    def test_unclosed_for_tag(self):
        with pytest.raises(UnclosedTagError, match="Unclosed.*for"):
            render_template("{% for x in items %}{{ x }}", {"items": []})

    def test_unexpected_else(self):
        with pytest.raises(TemplateSyntaxError, match="Unexpected closing tag"):
            render_template("{% else %}test", {})

    def test_unexpected_endif(self):
        with pytest.raises(TemplateSyntaxError, match="Unexpected closing tag"):
            render_template("{% endif %}", {})

    def test_unexpected_endfor(self):
        with pytest.raises(TemplateSyntaxError, match="Unexpected closing tag"):
            render_template("{% endfor %}", {})

    def test_endif_inside_for(self):
        with pytest.raises(TemplateSyntaxError):
            render_template("{% for x in items %}{% endif %}{% endfor %}", {"items": []})

    def test_endfor_inside_if(self):
        with pytest.raises(TemplateSyntaxError):
            render_template("{% if true %}{% endfor %}{% endif %}", {})

    def test_invalid_loop_syntax(self):
        with pytest.raises(InvalidLoopError, match="Invalid for loop syntax"):
            render_template("{% for items %}{% endfor %}", {"items": []})

    def test_loop_over_string(self):
        with pytest.raises(InvalidLoopError, match="Cannot iterate"):
            render_template("{% for c in text %}{{ c }}{% endfor %}", {"text": "hello"})

    def test_loop_over_number(self):
        with pytest.raises(InvalidLoopError, match="Cannot iterate"):
            render_template("{% for x in num %}{{ x }}{% endfor %}", {"num": 42})

    def test_loop_over_dict(self):
        with pytest.raises(InvalidLoopError, match="Cannot iterate"):
            render_template("{% for k in d %}{{ k }}{% endfor %}", {"d": {"a": 1}})

    def test_empty_condition(self):
        with pytest.raises(InvalidConditionError, match="Empty condition"):
            render_template("{% if %}test{% endif %}", {})

    def test_unknown_tag(self):
        with pytest.raises(TemplateSyntaxError, match="Unknown tag"):
            render_template("{% something %}test", {})


class TestTemplateEngineClass:
    def test_engine_instance_render(self):
        engine = TemplateEngine()
        result = engine.render("Hello, {{ name }}!", {"name": "World"})
        assert result == "Hello, World!"

    def test_engine_custom_placeholder(self):
        engine = TemplateEngine(undefined_placeholder="???")
        result = engine.render("Value: {{ x }}", {})
        assert result == "Value: ???"

    def test_engine_strict_mode(self):
        engine = TemplateEngine(strict=True)
        with pytest.raises(VariableNotFoundError):
            engine.render("{{ x }}", {})

    def test_engine_reuse(self):
        engine = TemplateEngine()
        r1 = engine.render("{{ a }}", {"a": "1"})
        r2 = engine.render("{{ b }}", {"b": "2"})
        assert r1 == "1"
        assert r2 == "2"


class TestEdgeCases:
    def test_braces_in_text(self):
        result = render_template("Use {{ var }} for replacement", {"var": "VALUE"})
        assert result == "Use VALUE for replacement"

    def test_empty_variable_name(self):
        result = render_template("{{ }}", {"": "test"})
        assert result == "test"

    def test_special_characters_in_variable_value(self):
        result = render_template(
            "{{ content }}",
            {"content": "<script>alert('xss')</script>"},
        )
        assert result == "<script>alert('xss')</script>"

    def test_unicode_values(self):
        result = render_template("Hello, {{ name }}!", {"name": "世界"})
        assert result == "Hello, 世界!"

    def test_unicode_variable_names(self):
        result = render_template("{{ 名称 }}", {"名称": "值"})
        assert result == "值"

    def test_escaping_not_performed(self):
        result = render_template("{{ text }}", {"text": "a & b < c"})
        assert result == "a & b < c"

    def test_nested_with_some_undefined(self):
        result = render_template(
            "{{ a.b }} and {{ c.d }}",
            {"a": {"b": "ok"}, "c": {}},
        )
        assert result == "ok and "

    def test_equality_with_none_literal(self):
        result = render_template(
            "{% if x == none %}Null{% else %}Not null{% endif %}",
            {"x": None},
        )
        assert result == "Null"

    def test_equality_with_null_literal(self):
        result = render_template(
            "{% if x == null %}Null{% else %}Not null{% endif %}",
            {"x": None},
        )
        assert result == "Null"

    def test_float_equality(self):
        result = render_template(
            "{% if x == 3.14 %}Pi{% else %}Not pi{% endif %}",
            {"x": 3.14},
        )
        assert result == "Pi"
