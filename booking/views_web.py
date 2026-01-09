from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required(login_url='/login/')
def booking_list_view(request):
    """
    Booking list web interface
    Requires user to be logged in
    """
    return render(request, 'booking/list.html', {
        'user': request.user
    })


@login_required(login_url='/login/')
def booking_create_view(request):
    """
    Create new booking web interface
    Requires user to be logged in
    """
    from .models import Motorcycle
    
    # Get user's motorcycles for selection
    motorcycles = Motorcycle.objects.filter(owner=request.user).order_by('-created_at')
    
    return render(request, 'booking/create.html', {
        'user': request.user,
        'motorcycles': motorcycles
    })


@login_required(login_url='/login/')
def motorcycles_view(request):
    """
    Motorcycles list web interface
    Requires user to be logged in
    """
    from .models import Motorcycle
    
    # Get user's motorcycles
    motorcycles = Motorcycle.objects.filter(owner=request.user).order_by('-created_at')
    
    return render(request, 'booking/motorcycles.html', {
        'user': request.user,
        'motorcycles': motorcycles
    })
