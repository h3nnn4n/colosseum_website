from django import template


register = template.Library()

ELO_CHANGE_ICONS = {
    "same": "fa-minus",
    "down": "fa-angle-down",
    "double-down": "fa-angle-double-down",
    "up": "fa-angle-up",
    "double-up": "fa-angle-double-up",
}


@register.inclusion_tag("elo_change.html")
def elo_change(value):
    if value == 0:
        icon = ELO_CHANGE_ICONS["same"]
        color_class = "text-muted"
    elif value < -10:
        icon = ELO_CHANGE_ICONS["double-down"]
        color_class = "text-danger"
    elif value < -5:
        icon = ELO_CHANGE_ICONS["down"]
        color_class = "text-danger"
    elif value > 10:
        icon = ELO_CHANGE_ICONS["double-up"]
        color_class = "text-success"
    elif value > 5:
        icon = ELO_CHANGE_ICONS["up"]
        color_class = "text-success"

    return {"icon": icon, "elo": value, "color_class": color_class}


@register.filter
def lower(value):
    return value.lower()
