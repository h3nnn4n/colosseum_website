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


class AgentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(AgentForm, self).__init__(*args, **kwargs)

    name = forms.CharField(max_length=50)
    active = forms.BooleanField()
    file = forms.FileField()

    class Meta:
        model = models.Agent
        fields = ("name", "active", "file")

    def save(self, commit=True):
        agent = super(AgentForm, self).save(commit=False)

        if self.user:
            agent.owner = self.user

        agent.file_hash = utils.hash_file(agent.file)

        if commit:
            agent.save()

        return agent
