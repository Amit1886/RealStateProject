from django.http import HttpResponse

def party_disabled(request):
    return HttpResponse("Party module disabled")
