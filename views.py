from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.conf import settings
from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from clients.models import *
from lawyers.models import Lawyers
from admin.models import *
from LCMS.decorators import *
from django.db.models import Q
from datetime import datetime
from django.core import serializers
import json
import re
import PyPDF2


# Create your views here.


# Create your views here.
def login(request):
    if "lawyers_login" in request.session:
        return redirect(reverse('lawyers:dashboard'))
    err = request.GET.get('err')
    print(request.session.keys())
    return render(request, 'lawyers/login.html', {"err":err})


def auth(request):
    if "lawyers_login" in request.session:
        return redirect(reverse('lawyers:dashboard'))
    if request.method == "POST":
        data = request.POST
        user = Lawyers.objects.filter(username=data.get('username'), password=data.get('password')).first()
        if not user == None:
            request.session['lawyers_login'] = user.name
            request.session['lawyers_login_id'] = user.id
            return redirect(reverse('lawyers:dashboard'))
        else:
            return redirect(reverse('lawyers:login')+"?err=true")
    else:
        return redirect(reverse('lawyers:login')+"?err=true")

def logout(request):
    if "lawyers_login" in request.session:
        del request.session['lawyers_login']
    return redirect(reverse('lawyers:login'))

@isLoggedIn
def dashboard(request):
    id = request.session['lawyers_login_id']
    lawyer = Lawyers.objects.get(id=id)
    ccases = CaseLawyers.objects.filter(case__status__name="Closed",lawyer=lawyer)
    rcases = CaseLawyers.objects.filter(case__status__name="Active",lawyer=lawyer)
    lawyer_clients_id = CaseLawyers.objects.filter(lawyer=lawyer).values('case__client')
    clients = Clients.objects.filter(status="Y",id__in=lawyer_clients_id)
    return render(request, 'lawyers/dashboard.html',{"ccases": ccases,"rcases": rcases,"clients": clients })


@isLoggedIn
def profile(request):
    page_name = "My Profile"
    id = request.session['lawyers_login_id']
    lawyer = Lawyers.objects.get(id=id)
    specializations = lawyer.specialization.all()
    cases = CaseLawyers.objects.filter(lawyer__id=id).values_list('case')
    hearings = Hearings.objects.filter(case__in = cases).order_by('date')
    fought_cases = CaseLawyers.objects.filter(lawyer__id=id, case__status='2')
    now = datetime.now()
    return render(request, 'lawyers/lawyer_view.html', {"page_name": page_name, "lawyer": lawyer, "specializations": specializations, "cases":cases, "hearings":hearings, "fought_cases":fought_cases, "now":now})


@isLoggedIn
def cases(request):
    page_name = "My Cases"
    id = request.session['lawyers_login_id']
    cases = CaseLawyers.objects.filter(lawyer__id=id)
    return render(request, 'lawyers/cases.html', {"page_name": page_name, "cases":cases})


@isLoggedIn
def case(request, case_number):
    page_name = "Case Details"
    case = Cases.objects.get(id=case_number)
    docs = CaseDocuments.objects.filter(case=case)
    hearings = Hearings.objects.filter(case=case)
    history = CaseHistory.objects.filter(case=case)
    case_points = CasePoints.objects.filter(case=case)
    peoples = CasePeoples.objects.filter(case=case)
    lawyers = case_lawyers = CaseLawyers.objects.filter(case__case_no=case.case_no)
    lawyers = []
    for l in case_lawyers:
        lawyers.append(l.lawyer.name)
    return render(request, 'lawyers/case_view.html', {"page_name": page_name, "case": case, "docs":docs, "hearings":hearings, "history":history,"case_points":case_points, 'peoples':peoples, 'lawyers':lawyers})



@isLoggedIn
def cases_close(request, case_number):
    Cases.objects.filter(id=case_number).update(status="2")
    CaseHistory.objects.create(case__id=case_number,action_performer="Lawyer", history='Marked Case As Close.')
    return redirect(reverse('lawyers:cases'))



@isLoggedIn
def case_add_people(request,case_id):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=case_id)
        CasePeoples.objects.create(case=case, relation=data.get('relation'), detail=data.get('detail'), name=data.get('name'))
        CaseHistory.objects.create(case=case,action_performer="Lawyer", history='Added '+data.get('name')+' to case People')
    return redirect(reverse("lawyers:case_view",kwargs={'case_number': case_id}))

@isLoggedIn
def case_add_history(request,case_id):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=case_id)
        CaseHistory.objects.create(case=case, history=data.get('history'), date=data.get('date'))
    return redirect(reverse("lawyers:case_view",kwargs={'case_number': case_id}))

@isLoggedIn
def case_add_points(request,case_id):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=case_id)
        CasePoints.objects.create(case=case, case_point=data.get('case_point'), date=data.get('date'))
        CaseHistory.objects.create(case=case,action_performer="Lawyer", history='Added Case Point')
    return redirect(reverse("lawyers:case_view",kwargs={'case_number': case_id}))

@isLoggedIn
def case_download_doc(request):
    filename = request.GET.get('file');
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        return HttpResponse("The requested file does not exist.")

@isLoggedIn
def case_studies(request):
    page_name = "Case Studies"
    cases = Cases.objects.all()
    case_studies = CaseStudies.objects.all()
    return render(request, 'lawyers/case_studies.html', {"page_name": page_name, "cases": cases, "case_studies": case_studies})


@isLoggedIn
def hearings(request):
    page_name = "Hearings"
    id = request.session['lawyers_login_id']
    cases = CaseLawyers.objects.filter(lawyer__id=id).values_list('case')
    hearings = Hearings.objects.filter(case__in=cases)
    return render(request, 'lawyers/hearings.html', {"page_name": page_name, "hearings":hearings})


@isLoggedIn
def hearing(request, hearing_id):
    page_name = "View Hearings"
    id = request.session['lawyers_login_id']
    cases = Cases.objects.all()
    hearingStatus = HearingStatus.objects.all()
    hearing = Hearings.objects.filter(id=hearing_id, case__lawyer=id)
    if not hearing:
        raise Http404("MyModel with id=1 does not exist")
    return render(request, 'lawyers/hearing_view.html', {"page_name": page_name,"cases":cases, "hearingStatus":hearingStatus, "hearing":hearing})

@isLoggedIn
def hearing_add(request):
    page_name = "Add New Hearing"
    id = request.session['lawyers_login_id']
    cases = CaseLawyers.objects.filter(lawyer__id=id)
    hearingStatus = HearingStatus.objects.all()
    return render(request, 'lawyers/hearing_add.html', {"page_name": page_name, "cases":cases, "hearingStatus":hearingStatus})


@isLoggedIn
def hearing_insert(request):
    if request.method == 'POST':
        data = request.POST
        hearing = Hearings.objects.create(judgment=data.get("judgement"), date=data.get("date"), case=Cases.objects.get(id= data.get('case')), status=HearingStatus.objects.get(id=data.get('status')))
        CaseHistory.objects.create(case=hearing.case,action_performer="Lawyer", history='Hearing Added')
    return redirect(reverse("lawyers:hearings"))

@isLoggedIn
def hearing_edit(request, hearing_id):
    page_name = "Edit Hearings"
    id = request.session['lawyers_login_id']
    cases = Cases.objects.filter(id__in = CaseLawyers.objects.filter(lawyer__id=id).values_list('case'))
    hearingStatus = HearingStatus.objects.all()
    hearing = Hearings.objects.get(id=hearing_id)
    return render(request, 'lawyers/hearing_edit.html', {"page_name": page_name,"cases":cases, "hearingStatus":hearingStatus, "hearing":hearing})

@isLoggedIn
def hearing_update(request):
    if request.method == 'POST':
        data = request.POST
        hearing = Hearings.objects.filter(id=data.get('id')).update(judgment=data.get("judgement"), date=data.get("date"), case=Cases.objects.get(id= data.get('case')), status=HearingStatus.objects.get(id=data.get('status')))
        CaseHistory.objects.create(case=Cases.objects.get(id= data.get('case')),action_performer="Lawyer", history="Hearing Details Modified")
    return redirect(reverse("lawyers:hearings"))


@isLoggedIn
def case_study_download(request):
    filename = request.GET.get('filename')
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    print(open(file_path, 'rb'))
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        return HttpResponse("The requested file does not exist.")
    
@isLoggedIn
def messages(request):
    page_name = "Messages"
    id = request.session['lawyers_login_id']
    cases = CaseLawyers.objects.filter(lawyer__id=id).values_list('case', flat=True)
    unique_clients = Clients.objects.filter(id__in = Cases.objects.filter(id__in = cases).values_list('client', flat=True)).distinct()
    messages = Messages.objects.filter(Q(sender_lawyer=id) | Q(receiver_lawyer=id))
    return render(request, 'lawyers/messages.html', {"page_name": page_name, "messages":messages, "clients":unique_clients})


@isLoggedIn
def message_send(request):
    id = request.session['lawyers_login_id']
    user = Lawyers.objects.get(id=id)
    if request.method == 'POST':
        data = request.POST
        client = Clients.objects.get(id=data.get('cl_id'))
        msg = Messages.objects.create(sender_lawyer=user, receiver_client=client, content=data.get('msg'))
        msg_dict = {'id': msg.id, 'sender_lawyer': msg.sender_lawyer.id, 'receiver_client': msg.receiver_client.id, 'content': msg.content, 'timestamp':msg.timestamp}
        return JsonResponse(msg_dict, safe=False)
    
@csrf_exempt
@isLoggedIn
def message_get(request):
    id = request.session['lawyers_login_id']
    user = Lawyers.objects.get(id=id)
    if request.method == 'POST':
        data = request.POST
        client = Clients.objects.filter(id=data.get('cl_id')).first()
        msgs = Messages.objects.filter((Q(sender_lawyer=user) & Q(receiver_client=client)) | (Q(sender_client=client) & Q(receiver_lawyer=user)))
    return JsonResponse(serializers.serialize('json', msgs), safe=False)

@isLoggedIn
def get_messages_clients(request):
    id = request.session['lawyers_login_id']
    user = Lawyers.objects.get(id=id)
    msgs = Messages.objects.filter(Q(sender_lawyer=user) | Q(receiver_lawyer=user))
    return JsonResponse(serializers.serialize('json', msgs), safe=False)



@isLoggedIn
def case_study_search(request):
    search_text = request.POST.get('search')
    folder_path = os.path.join(settings.MEDIA_ROOT, "case_studies")
    search_results = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                # extract the text content from the PDF file
                text = []
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text.append(page.extract_text().split('\n'))

                for page_num,lines in enumerate(text):
                    for line_no, line in enumerate(lines):
                        if re.search(search_text, line):
                            search_results.setdefault(filename, []).append(line)
                            print(line_no,line) 
    return HttpResponse(json.dumps(search_results),content_type='application/json')
    
