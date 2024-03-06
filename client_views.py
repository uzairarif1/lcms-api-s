from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse,JsonResponse
from django.conf import settings
from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from clients.models import *
from lawyers.models import Lawyers
from admin.models import *
from LCMS.decorators import *
from django.db.models import Q
from django.core import serializers

# Create your views here.

def login(request):
    if "clients_login" in request.session:
        return redirect(reverse('clients:dashboard'))
    err = request.GET.get('err')
    print(request.session.keys())
    return render(request, 'clients/login.html', {"err":err})


def auth(request):
    if "clients_login" in request.session:
        return redirect(reverse('clients:dashboard'))
    if request.method == "POST":
        data = request.POST
        user = Clients.objects.filter(username=data.get('username'), password=data.get('password')).first()
        if not user == None:
            request.session['clients_login'] = user.firstname
            request.session['clients_login_id'] = user.id
            return redirect(reverse('clients:dashboard'))
        else:
            return redirect(reverse('clients:login')+"?err=true")
    else:
        return redirect(reverse('clients:login')+"?err=true")

def logout(request):
    if "clients_login" in request.session:
        del request.session['clients_login']
    return redirect(reverse('clients:login'))


@isLoggedIn
def profile(request):
    id = request.session['clients_login_id']
    user = Clients.objects.get(id=id)
    cases = Cases.objects.filter(client=user).order_by('-id')
    page_name = "Personal Profile"
    return render(request, 'clients/profile.html',{"page_name":page_name, "client":user, "cases":cases})

@isLoggedIn
def cases(request):
    page_name = "My Cases"
    id = request.session['clients_login_id']
    cases = Cases.objects.filter(client=id)
    case_data=[]
    for case in cases:
        case_dict = {}
        case_dict['details'] = case
        case_lawyers = CaseLawyers.objects.filter(case__case_no=case.case_no)
        lawyers = []
        for l in case_lawyers:
            lawyers.append(l.lawyer.name)
        case_dict['lawyers'] = lawyers
        case_data.append(case_dict)
    return render(request, 'clients/cases.html', {"page_name": page_name, "cases":case_data})


@isLoggedIn
def case(request, case_number):
    page_name = "Case Details"
    case = Cases.objects.get(id=case_number)
    docs = CaseDocuments.objects.filter(case=case)
    hearings = Hearings.objects.filter(case=case)
    history = CaseHistory.objects.filter(case=case)
    case_points = CasePoints.objects.filter(case=case)
    peoples = CasePeoples.objects.filter(case=case)
    case_lawyers = CaseLawyers.objects.filter(case=case)
    lawyers = []
    for l in case_lawyers:
        lawyers.append(l.lawyer.name)
    return render(request, 'clients/case_view.html', {"page_name": page_name, "case": case, "docs":docs, "hearings":hearings, "history":history,"case_points":case_points, 'peoples':peoples, 'lawyers':lawyers})

@isLoggedIn
def case_download_doc(request):
    filename = request.GET.get('file')
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        return HttpResponse("The requested file does not exist.")
    
@isLoggedIn
def case_upload_doc(request):
    if request.method == 'POST':
        file =  request.FILES['doc']
        id = request.session['clients_login_id']
        user = Clients.objects.get(id=id)
        case = Cases.objects.filter(client=user).first()
        doc = handle_uploaded_file(file,"case_documents")
        CaseDocuments.objects.create(name=file.name.split('.')[0], case=case, path=doc)
        CaseHistory.objects.create(case=case,action_performer="Client", history='Added Case Document: '+file.name.split('.')[0])
    return redirect(reverse('clients:case_view', kwargs={'case_number':case.id}))

@isLoggedIn
def messages(request):
    page_name = "Messages"
    id = request.session['clients_login_id']
    # cases = Cases.objects.filter(client__id=id).values_list('id', flat=True)
    unique_lawyers = Lawyers.objects.filter(id__in = CaseLawyers.objects.filter(case__in = Cases.objects.filter(client__id=id)).values_list('lawyer', flat=True)).distinct()
    print(unique_lawyers     )
    messages = Messages.objects.filter(Q(sender_client=id) | Q(receiver_client=id))
    return render(request, 'clients/messages.html', {"page_name": page_name, "messages":messages, "lawyers":unique_lawyers})
    

@isLoggedIn
def message_send(request):
    id = request.session['clients_login_id']
    user = Clients.objects.get(id=id)
    if request.method == 'POST':
        data = request.POST
        lawyer = Lawyers.objects.get(id=data.get('cl_id'))
        msg = Messages.objects.create(sender_client=user, receiver_lawyer=lawyer, content=data.get('msg'))
        msg_dict = {'id': msg.id, 'sender_client': msg.sender_client.id, 'receiver_lawyer': msg.receiver_lawyer.id, 'content': msg.content, 'timestamp':msg.timestamp}
        return JsonResponse(msg_dict, safe=False)
    
@csrf_exempt
@isLoggedIn
def message_get(request):
    id = request.session['clients_login_id']
    user = Clients.objects.get(id=id)
    if request.method == 'POST':
        data = request.POST
        lawyer = Lawyers.objects.filter(id=data.get('cl_id')).first()
        msgs = Messages.objects.filter((Q(sender_client=user) & Q(receiver_lawyer=lawyer)) | (Q(sender_lawyer=lawyer) & Q(receiver_client=user)))
        print(msgs.query)
    return JsonResponse(serializers.serialize('json', msgs), safe=False)
