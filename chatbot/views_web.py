from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required(login_url='/login/')
def chatbot_view(request):
    """
    Chatbot web interface
    Requires user to be logged in
    """
    return render(request, 'chatbot/chat.html', {
        'user': request.user
    })
