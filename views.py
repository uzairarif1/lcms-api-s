from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from clients.models import *
from lawyers.models import Lawyers, Specialization
from admin.models import *
from LCMS.decorators import *
import json
import re
import PyPDF2

# Create your views here.
def login(request):
    if "admin_login" in request.session:
        return redirect(reverse('admin:dashboard'))
    err = request.GET.get('err')
    print(request.session.keys())
    return render(request, 'admin/login.html', {"err":err})


def auth(request):
    if "admin_login" in request.session:
        return redirect(reverse('admin:dashboard'))
    if request.method == "POST":
        data = request.POST
        user = Users.objects.filter(username=data.get('username'), password=data.get('password')).first()
        if not user == None:
            request.session['admin_login'] = user.first_name
            return redirect(reverse('admin:dashboard'))
        else:
            return redirect(reverse('admin:login')+"?err=true")
    else:
        return redirect(reverse('admin:login')+"?err=true")

def logout(request):
    if "admin_login" in request.session:
        del request.session['admin_login']
    return redirect(reverse('admin:login'))

@isLoggedIn
def dashboard(request):
    ccases = Cases.objects.filter(status__name="Closed")
    rcases = Cases.objects.filter(status__name="Active")
    clients = Clients.objects.filter(status="Y")
    lawyers = Lawyers.objects.filter(status="Y")
    return render(request, 'admin/dashboard.html',{"ccases": ccases,"rcases": rcases,"clients": clients,"lawyers": lawyers })


@isLoggedIn
def cases(request):
    page_name = "Cases"
    cases = Cases.objects.all().order_by('id')
    case_data = []
    for case in cases:
        case_dict = {}
        case_dict['details'] = case
        case_lawyers = CaseLawyers.objects.filter(case__case_no=case.case_no)
        lawyers = []
        for l in case_lawyers:
            lawyers.append(l.lawyer.name)
        case_dict['lawyers'] = lawyers
        # print((case_lawyers))
        # histories = CaseLawyersTransferHistory.objects.filter(case=case)
        # transfer_history = []
        # for h in histories:
        #     h_dict = {"comment":h.comment, "id":h.id, "tfrom":h.transferd_from.name, "tto":h.transferd_to.name}
        #     transfer_history.append(h_dict)            
        # case_dict['lawyer_history_json'] = json.dumps(transfer_history)
        case_data.append(case_dict)
    lawyers = Lawyers.objects.filter(status="Y")
    return render(request, 'admin/cases.html',{"page_name":page_name, "cases": case_data, "lawyers":lawyers})


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
    return render(request, 'admin/case_view.html', {"page_name": page_name, "case": case, "docs":docs, "hearings":hearings, "history":history,"case_points":case_points, 'peoples':peoples, 'lawyers':lawyers})

@isLoggedIn
def case_add(request):
    page_name = "Add New Case"
    lawyers = Lawyers.objects.all()
    clients = Clients.objects.all()
    judges = Judges.objects.filter(status='Y')
    case_types = CaseTypes.objects.all()
    case_statuses = CaseStatuses.objects.all()
    cases = Cases.objects.all()
    return render(request, 'admin/case_add.html', {"page_name": page_name, "lawyers": lawyers, "clients": clients, "judges": judges, "case_types": case_types, "case_statuses":case_statuses, "cases":cases})

@isLoggedIn
def case_insert(request):
    if request.method == 'POST':
        data = request.POST
        print(data)
        case = Cases.objects.create(case_no=data.get("case_no"), type=CaseTypes.objects.get(id=data.get("type")), title=data.get("title"), start_date=data.get("start_date"), description=data.get("description"), status=CaseStatuses.objects.get(id=data.get("status")), client=Clients.objects.get(id=data.get("client")), judge=Judges.objects.get(id=data.get("judge")))
        CaseHistory.objects.create(case=case,action_performer="Admin", history="Case Created")
        if not data.get('mlawyer') == None:
            for l in data.get('mlawyer'):
                lawyer = Lawyers.objects.get(id=l)
                CaseLawyers.objects.create(case=case,lawyer=lawyer,type='1')
                CaseHistory.objects.create(case=case,action_performer="Admin", history="Assigned "+ lawyer.name +" as Main Lawyer")
        if not data.get('alawyer') == None:
            for l in data.get('alawyer'):
                lawyer = Lawyers.objects.get(id=l)
                CaseLawyers.objects.create(case=case,lawyer=lawyer,type='2')
                CaseHistory.objects.create(case=case,action_performer="Admin", history="Assigned "+ lawyer.name +" as Assosiate Lawyer")
    return redirect(reverse("admin:cases"))

@isLoggedIn
def case_update(request):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=data.get('case_id'))
        Cases.objects.filter(id=data.get('case_id')).update(type=CaseTypes.objects.get(id=data.get("type")), title=data.get("title"), start_date=data.get("start_date"), description=data.get("description"), status=CaseStatuses.objects.get(id=data.get("status")), client=Clients.objects.get(id=data.get("client")), judge=Judges.objects.get(id=data.get("judge")))
        CaseHistory.objects.create(case=case,action_performer="Admin", history="Case Details Modified")
        case_lawyers = CaseLawyers.objects.filter(case=case)
        lawyer_ids_initial = list(case_lawyers.values_list('lawyer__id', flat=True))
        case_lawyers.delete() 
        print(lawyer_ids_initial)
        for l in data.get('mlawyer'):
            CaseLawyers.objects.create(case=case,lawyer=Lawyers.objects.get(id=l),type='1')
        for l in data.get('alawyer'):
            CaseLawyers.objects.create(case=case,lawyer=Lawyers.objects.get(id=l),type='2')
        updated_case_lawyers = CaseLawyers.objects.filter(case=case)
        lawyer_ids_updated = list(updated_case_lawyers.values_list('lawyer__id', flat=True))
        added_lawyer_ids = list(set(lawyer_ids_updated) - set(lawyer_ids_initial))
        removed_lawyer_ids = list(set(lawyer_ids_initial) - set(lawyer_ids_updated))
        print(lawyer_ids_initial,'lawyer_ids_initial')
        print(lawyer_ids_updated,'updated_case_lawyers')

        for l in added_lawyer_ids:
            lr = Lawyers.objects.get(id=l)
            print(lr,1)
            CaseHistory.objects.create(case=case,action_performer="Admin", history="Assigned case to "+ lr.name) 
        
        for l in removed_lawyer_ids:
            lr = Lawyers.objects.get(id=l)
            print(lr,2)
            CaseHistory.objects.create(case=case,action_performer="Admin", history="Removed "+ lr.name+" from case")

    return redirect(reverse("admin:cases"))

@isLoggedIn
def case_edit(request, case_number):
    page_name = "Update Case"
    lawyers = Lawyers.objects.all()
    clients = Clients.objects.all()
    judges = Judges.objects.filter(status='Y')
    case_types = CaseTypes.objects.all()
    case_statuses = CaseStatuses.objects.all()
    case = Cases.objects.get(id=case_number)
    case_lawyers = CaseLawyers.objects.filter(case=case)
    mlawyers = []
    alawyers = []
    for cl in case_lawyers:
        if cl.type == '1':
            mlawyers.append(cl.lawyer.id)
        elif cl.type == '2':
            alawyers.append(cl.lawyer.id)

    return render(request, 'admin/case_edit.html', {"page_name": page_name, "lawyers": lawyers, "clients": clients, "judges": judges, "case_types": case_types, "case_statuses":case_statuses, "case":case, "mlawyers":mlawyers,"alawyers":alawyers})

@isLoggedIn
def case_transfer(request):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=data.get('case'))
        new_lawyer = Lawyers.objects.get(id=data.get('lawyer'))
        CaseLawyersTransferHistory.objects.create(case=case, comment=data.get("comment"),transferd_to=new_lawyer, transferd_from=case.lawyer)
        case.lawyer=new_lawyer
        case.save()
    return redirect(reverse("admin:cases"))

@isLoggedIn
def cases_close(request, case_id):
    Cases.objects.filter(id=case_id).update(status="2")
    CaseHistory.objects.create(case=case,action_performer="Admin", history='Case Markded As Close')
    return redirect(reverse('admin:cases'))


@isLoggedIn
def case_add_people(request,case_id):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=case_id)
        CasePeoples.objects.create(case=case, relation=data.get('relation'), detail=data.get('detail'), name=data.get('name'))
        CaseHistory.objects.create(case=case,action_performer="Admin", history='Added '+data.get('name')+' to case People')
    return redirect(reverse("admin:case_view",kwargs={'case_number': case_id}))

@isLoggedIn
def case_add_history(request,case_id):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=case_id)
        CaseHistory.objects.create(case=case, history=data.get('history'), date=data.get('date'))
    return redirect(reverse("admin:case_view",kwargs={'case_number': case_id}))

@isLoggedIn
def case_add_points(request,case_id):
    if request.method == 'POST':
        data = request.POST
        case = Cases.objects.get(id=case_id)
        CasePoints.objects.create(case=case, case_point=data.get('case_point'), date=data.get('date'))
        CaseHistory.objects.create(case=case,action_performer="Admin", history='Added Case Point')
    return redirect(reverse("admin:case_view",kwargs={'case_number': case_id}))


@isLoggedIn
def lawyers(request):
    page_name = "Lawyers"
    lawyers = Lawyers.objects.all().order_by('id')
    return render(request, 'admin/lawyers.html',{"page_name":page_name, "lawyers":lawyers})

@isLoggedIn
def specialization_insert(request):
    if request.method != "POST":
        return HttpResponse('<h3>404 Page Not Found!</h3>')
    else:
        name = request.POST.get('name')
        Specialization.objects.create(name=name)
        return redirect(reverse("admin:lawyers"))

@isLoggedIn
def lawyer(request, lawyer_id):
    page_name = "Lawyer Details"
    lawyer = Lawyers.objects.get(id=lawyer_id)
    specializations = lawyer.specialization.all()
    cases = CaseLawyers.objects.filter(lawyer__id=lawyer_id).values_list('case')
    hearings = Hearings.objects.filter(case__in = cases).order_by('date')
    fought_cases = CaseLawyers.objects.filter(lawyer__id=lawyer_id, case__status='2')
    return render(request, 'admin/lawyer_view.html', {"page_name": page_name, "lawyer": lawyer, "specializations": specializations, "cases":cases, "hearings":hearings, "fought_cases":fought_cases})

@isLoggedIn
def lawyer_add(request):
    page_name = "Add New Lawyer"
    specializations = Specialization.objects.all()
    return render(request, 'admin/lawyer_add.html', {"page_name": page_name, "specializations":specializations})

@isLoggedIn
def lawyer_insert(request):
    if request.method == 'POST':
        data = request.POST
        img =  request.FILES.get('image',False)
        img = handle_uploaded_file(img,"lawyers")
        print(img)
        lawyer = Lawyers.objects.create(name=data.get("name"), tag=data.get("tag"), education=data.get("education"), address=data.get("address"), status="Y", image=img, short_description=data.get("description"), username=data.get("username"), password=data.get("password"))
        for id in data.get("specialization"):
            spec = Specialization.objects.get(id=id)
            lawyer.specialization.add(spec)
    return redirect(reverse("admin:lawyers"))


@isLoggedIn
def lawyer_edit(request, lawyer_id):
    page_name = "Edit Lawyer"
    specializations = Specialization.objects.all()
    lawyer = Lawyers.objects.get(id=lawyer_id)
    return render(request, 'admin/lawyer_edit.html', {"page_name": page_name, "specializations":specializations, 'lawyer':lawyer})

@isLoggedIn
def lawyer_update(request):
    if request.method == 'POST':
        data = request.POST
        img =  request.FILES.get('image',False)
        img = handle_uploaded_file(img,"lawyers")
        Lawyers.objects.filter(id=data.get('id')).update(name=data.get("name"), tag=data.get("tag"), education=data.get("education"), address=data.get("address"), image=img, short_description=data.get("description"), password=data.get("password"))
        lawyer = Lawyers.objects.get(id=data.get('id'))
        lawyer.specialization.clear()
        for id in data.getlist("specialization"):
            spec = Specialization.objects.get(id=id)
            lawyer.specialization.add(spec)
    return redirect(reverse("admin:lawyers"))

@isLoggedIn
def clients(request):
    page_name = "Clients"
    clients = Clients.objects.all().order_by('id')
    return render(request, 'admin/clients.html', {"page_name": page_name,"clients": clients})


@isLoggedIn
def client(request, client_id):
    page_name = "Client Details"
    cases = Cases.objects.filter(client=client_id).prefetch_related('casedocuments_set').order_by('-start_date')
    client = Clients.objects.get(id=client_id)
    return render(request, 'admin/client_view.html', {"page_name": page_name, "client": client, "cases": list(cases)})


@isLoggedIn
def client_add(request):
    page_name = "Add New Clients"
    return render(request, 'admin/client_add.html', {"page_name": page_name})


@isLoggedIn
def client_insert(request):
    if request.method == 'POST':
        data = request.POST
        Clients.objects.create(firstname = data.get('firstname'), lastname = data.get('lastname'), address = data.get('address'), email = data.get('email'), phone = data.get('phone'), gov_id = data.get('gov_id'), description = data.get('description'), image = "default.png", status = 'Y', username = data.get('username'), password = data.get('password'))
    return redirect(reverse("admin:clients"))


@isLoggedIn
def client_edit(request,client_id):
    page_name = "Add New Clients"
    client = Clients.objects.get(id=client_id)
    return render(request, 'admin/client_edit.html', {"page_name": page_name, 'client':client})


@isLoggedIn
def client_update(request):
    if request.method == 'POST':
        data = request.POST
        Clients.objects.filter(id=data.get('id')).update(firstname = data.get('firstname'), lastname = data.get('lastname'), address = data.get('address'), email = data.get('email'), phone = data.get('phone'), gov_id = data.get('gov_id'), description = data.get('description'), image = "default.png", status = 'Y', password = data.get('password'))
    return redirect(reverse("admin:clients"))

@isLoggedIn
def client_upload_doc(request):
    if request.method == 'POST':
        data = request.POST
        file =  request.FILES['doc']
        case = Cases.objects.get(id = data.get('case'))
        doc = handle_uploaded_file(file,"case_documents")
        CaseDocuments.objects.create(name=file.name.split('.')[0], case=case, path=doc)
    return redirect(reverse('admin:case_view', kwargs={'case_number': case.id}))

@isLoggedIn
def client_download_doc(request):
    filename = request.GET.get('file');
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        return HttpResponse("The requested file does not exist.")

@isLoggedIn
def hearings(request):
    page_name = "Hearings"
    hearings = Hearings.objects.all()
    return render(request, 'admin/hearings.html', {"page_name": page_name, "hearings":hearings})

@isLoggedIn
def hearing_status_insert(request):
    if request.method == 'POST':
        data = request.POST
        HearingStatus.objects.create(name=data.get("name"), status="Y")
    return redirect(reverse("admin:hearings"))

@isLoggedIn
def hearing(request, hearing_id):
    page_name = "View Hearings"
    cases = Cases.objects.all()
    hearingStatus = HearingStatus.objects.all()
    hearing = Hearings.objects.get(id=hearing_id)
    return render(request, 'admin/hearing_view.html', {"page_name": page_name,"cases":cases, "hearingStatus":hearingStatus, "hearing":hearing})

@isLoggedIn
def hearing_add(request):
    page_name = "Add New Hearing"
    cases = Cases.objects.all()
    hearingStatus = HearingStatus.objects.all()
    return render(request, 'admin/hearing_add.html', {"page_name": page_name, "cases":cases, "hearingStatus":hearingStatus})


@isLoggedIn
def hearing_insert(request):
    if request.method == 'POST':
        data = request.POST
        hearing = Hearings.objects.create(judgment=data.get("judgement"), date=data.get("date"), case=Cases.objects.get(id= data.get('case')), status=HearingStatus.objects.get(id=data.get('status')))
        CaseHistory.objects.create(case = hearing.case ,action_performer="Admin", history="Hearing Added")
    return redirect(reverse("admin:hearings"))

@isLoggedIn
def hearing_edit(request, hearing_id):
    page_name = "View Hearings"
    cases = Cases.objects.all()
    hearingStatus = HearingStatus.objects.all()
    hearing = Hearings.objects.get(id=hearing_id)
    return render(request, 'admin/hearing_edit.html', {"page_name": page_name,"cases":cases, "hearingStatus":hearingStatus, "hearing":hearing})

@isLoggedIn
def hearing_update(request):
    if request.method == 'POST':
        data = request.POST
        hearing = Hearings.objects.filter(id=data.get('id')).update(judgment=data.get("judgement"), date=data.get("date"), case=Cases.objects.get(id= data.get('case')), status=HearingStatus.objects.get(id=data.get('status')))
        CaseHistory.objects.create(case=Cases.objects.get(id= data.get('case')),action_performer="Admin", history="Hearing Details Modified")
    return redirect(reverse("admin:hearings"))


@isLoggedIn
def case_studies(request):
    page_name = "Case Studies"
    cases = Cases.objects.all()
    case_studies = CaseStudies.objects.all()
    return render(request, 'admin/case_studies.html', {"page_name": page_name, "cases": cases, "case_studies": case_studies})


@isLoggedIn
def case_study_insert(request):
    if request.method == 'POST':
        data = request.POST
        pdf =  request.FILES['doc']
        doc = handle_uploaded_file(pdf,"case_studies")
        CaseStudies.objects.create(name=data.get('name'),tags=data.get('tags'), documnet=doc)
    return redirect(reverse("admin:case_studies"))

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
def judges(request):
    judges=Judges.objects.filter(status="Y")
    return render(request, 'admin/judges.html',{"judges":judges})


@isLoggedIn
def judge_insert(request):
    if request.method == 'POST':
        data = request.POST
    Judges.objects.create(name=data.get('name'), status="Y")
    return redirect(reverse("admin:judges"))

@isLoggedIn
def judge_delete(request, judge_id):
    Judges.objects.filter(id=judge_id).update(status="N")
    return redirect(reverse("admin:judges"))



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
    
