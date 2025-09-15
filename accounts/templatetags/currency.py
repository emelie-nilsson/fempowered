from django import template

register = template.Library()


@register.filter
def eur(cents):
    """Int cents -> '€54.99' EU-format."""
    try:
        val = int(cents) / 100
    except Exception:
        return "€0,00"
    s = f"{val:,.2f}"  # 1,234.56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234,56
    return f"€{s}"
