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
    elif value < -10:
        icon = ELO_CHANGE_ICONS["double-down"]
    elif value < -5:
        icon = ELO_CHANGE_ICONS["down"]
    elif value > 10:
        icon = ELO_CHANGE_ICONS["double-up"]
    elif value > 5:
        icon = ELO_CHANGE_ICONS["up"]

    return {"icon": icon, "elo": value}


@register.filter
def lower(value):
    return value.lower()
