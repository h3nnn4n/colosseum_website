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
    if value is None:
        return {
            "icon": ELO_CHANGE_ICONS["same"],
            "elo": "-",
            "color_class": "text-muted",
        }

    if value < -10:
        icon = ELO_CHANGE_ICONS["double-down"]
        color_class = "text-danger"
    elif value < 0:
        icon = ELO_CHANGE_ICONS["down"]
        color_class = "text-danger"
    elif value > 10:
        icon = ELO_CHANGE_ICONS["double-up"]
        color_class = "text-success"
    elif value > 0:
        icon = ELO_CHANGE_ICONS["up"]
        color_class = "text-success"
    else:
        icon = ELO_CHANGE_ICONS["same"]
        color_class = "text-muted"

    elo = str(int(abs(value)))

    return {"icon": icon, "elo": elo, "color_class": color_class}
