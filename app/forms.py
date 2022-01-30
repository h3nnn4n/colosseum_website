from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from . import models, utils


class NewUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserForm(forms.ModelForm):
    username = forms.CharField(max_length=50)
    email = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ("username", "email")


class AgentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(AgentForm, self).__init__(*args, **kwargs)
        self.fields["game_id"] = forms.CharField(
            label="Game",
            widget=forms.Select(
                choices=[
                    (game.id, game.name)
                    for game in models.Game.objects.filter(active=True)
                ]
            ),
        )

    name = forms.CharField(max_length=50)
    game_id = forms.CharField(label="Game", widget=forms.Select())
    active = forms.BooleanField()
    file = forms.FileField()

    class Meta:
        model = models.Agent
        fields = ("name", "game_id", "active", "file")

    def save(self, commit=True):
        agent = super(AgentForm, self).save(commit=False)

        if self.user:
            agent.owner = self.user

        game_id = self.data["game_id"]
        agent.file_hash = utils.hash_file(agent.file)
        agent.game = models.Game.objects.get(id=game_id)

        if commit:
            agent.save()
            if not agent.ratings.filter(
                season__active=True, season__main=True
            ).exists():
                season = models.Season.objects.filter(active=True, main=True).first()
                if season:
                    models.AgentRatings.objects.create(
                        season=season, agent=agent, game=agent.game
                    )

        return agent
