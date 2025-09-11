from django.shortcuts import render

def handler404(request, exception, template_name="404.html"):
    return render(request, template_name, status=404)

def handler500(request, template_name="500.html"):
    return render(request, template_name, status=500)
