from django.shortcuts import redirect
from django.urls import reverse

def save_profile(backend, user, response, *args, **kwargs):
    """
    Agar user ke paas mobile number nahi hai to 
    profile complete karne ke liye redirect kare.
    """
    profile = user.userprofile  

    if not profile.mobile:  # Agar mobile missing hai
        return redirect(reverse('complete-profile'))
