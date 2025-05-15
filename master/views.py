from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages

def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'master/login.html', {'error': 'Invalid credentials'})
    return render(request, 'master/login.html')

@login_required
def dashboard_view(request):
    return render(request, 'master/dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('login')
from django.shortcuts import render, redirect
from .forms import ExcelUploadForm
from .models import ExcelUpload, StudentRecord
import pandas as pd
import os
def student_data_view(request):
    upload_form = ExcelUploadForm()
    files = ExcelUpload.objects.order_by('-uploaded_at')
    table_data = []

    # ✅ Handle file upload
    if request.method == 'POST' and 'upload_submit' in request.POST:
        upload_form = ExcelUploadForm(request.POST, request.FILES)
        if upload_form.is_valid():
            upload_form.save()
            return redirect('student_data_view')

    # ✅ Combine and read all Excel files
    all_files = ExcelUpload.objects.all()
    combined_df = pd.DataFrame()

    for file_obj in all_files:
        try:
            file_path = file_obj.file.path
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext == '.xlsx':
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                continue  # skip unknown types

            combined_df = pd.concat([combined_df, df], ignore_index=True)

        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    # ✅ Drop duplicates within Excel file data
    if not combined_df.empty:
        combined_df.drop_duplicates(subset=['Student ID', 'Student Name'], inplace=True)

        # ✅ Avoid inserting already saved DB records
        existing_records = StudentRecord.objects.values_list('student_id', 'student_name')
        existing_set = set((str(i).strip(), n.strip().lower()) for i, n in existing_records)

        for _, row in combined_df.iterrows():
            student_id = str(row.get('Student ID', '')).strip()
            student_name = str(row.get('Student Name', '')).strip().lower()

            if (student_id, student_name) not in existing_set:
                StudentRecord.objects.create(
                    student_id=student_id,
                    student_name=row.get('Student Name', ''),
                    guardian_name=row.get('Guardian Name', ''),
                    guardian_phone=row.get('Guardian Phone Number', ''),
                    guardian_relation=row.get('Guardian Relation with Student', ''),
                    department=row.get('Department', '')
                )
                existing_set.add((student_id, student_name))  # avoid re-saving in loop

    # ✅ Always show saved records from DB
    saved_records = StudentRecord.objects.all().values(
        'student_id', 'student_name', 'guardian_name',
        'guardian_phone', 'guardian_relation', 'department'
    )
    table_data = list(saved_records)

    return render(request, 'master/student_form.html', {
        'upload_form': upload_form,
        'files': files,
        'table_data': table_data
    })
#

# from .models import SentMessage, StudentRecord
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render

# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render
# from django.db.models import Q
# from .models import SentMessage, StudentRecord

# @login_required
# def message_history_view(request):
#     # Get filters from URL parameters
#     channel_filter = request.GET.get('channel', '')
#     status_filter = request.GET.get('status', '')
#     department = request.GET.get('department')

#     # Start with all sent messages ordered by 'sent_at' date
#     messages = SentMessage.objects.all().order_by('-sent_at')

#     # Apply channel filters (SMS or WhatsApp)
#     if channel_filter == 'sms':
#         messages = messages.filter(send_sms=True)
#     elif channel_filter == 'whatsapp':
#         messages = messages.filter(send_whatsapp=True)

#     # Apply status and department filters
#     if status_filter:
#         messages = messages.filter(status=status_filter)
#     if department:
#         messages = messages.filter(department=department)

#     # Get the list of departments for the filter dropdown
#     departments = SentMessage.objects.values_list('department', flat=True).distinct()

#     # Process each message and add status and guardian details
#     for msg in messages:
#         # Fetch guardians for the given department of the message
#         students = StudentRecord.objects.filter(department=msg.department)
#         msg.guardians = []

#         # Loop through the guardians to check the status of each one
#         for guardian in students:
#             guardian_status = "Not Delivered"

#             # Check delivery status based on the message channels (SMS/WhatsApp)
#             if msg.send_sms and msg.send_whatsapp:
#                 guardian_status = "Delivered via SMS and WhatsApp"
#             elif msg.send_sms:
#                 guardian_status = "Delivered via SMS"
#             elif msg.send_whatsapp:
#                 guardian_status = "Delivered via WhatsApp"
            
#             # Add the guardian details to the message status
#             msg.guardians.append({
#                 "student": guardian.student_name,
#                 "phone": guardian.guardian_phone,
#                 "status": guardian_status
#             })

#         # Human-readable status based on the message's state
#         if msg.status.lower() == "pending":
#             # If both SMS and WhatsApp failed or are still in progress, mark it as Pending
#             if not msg.send_sms and not msg.send_whatsapp:
#                 msg.status_display = "Not Delivered"
#             else:
#                 msg.status_display = "Pending"
#         else:
#             # If both SMS and WhatsApp were successful, mark it as Delivered
#             if msg.send_sms and msg.send_whatsapp:
#                 msg.status_display = "Delivered"
#             else:
#                 msg.status_display = "Not Delivered"

#     return render(request, 'master/message_history.html', {
#         'messages': messages,
#         'channel_filter': channel_filter,
#         'status_filter': status_filter,
#         'department_filter': department,
#         'departments': departments,
#     })


from django.shortcuts import render
from .models import StudentRecord, SentMessage
 
def dashboard_view(request):
    total_students = StudentRecord.objects.count()
    messages_sent = SentMessage.objects.count()
    active_departments = SentMessage.objects.values('department').distinct().count()
 
    # Calculate delivery status counts
    delivered_count = 0
    failed_count = 0
 
    all_messages = SentMessage.objects.all()
    for msg in all_messages:
        try:
            status_parts = dict(part.split(":") for part in msg.status.split() if ":" in part)
        except ValueError:
            status_parts = {}
 
        sms_status = status_parts.get("sms", "0")
        whatsapp_status = status_parts.get("whatsapp", "0")
 
        if sms_status == "1" or whatsapp_status == "1":
            delivered_count += 1
        else:
            failed_count += 1
 
    delivery_rate = round((delivered_count / messages_sent) * 100, 2) if messages_sent > 0 else 0
 
    # ✅ Recent 5 messages (delivered or not)
    recent_messages_qs = SentMessage.objects.order_by('-sent_at')[:5]
    recent_messages = []
 
    for msg in recent_messages_qs:
        try:
            status_parts = dict(part.split(":") for part in msg.status.split() if ":" in part)
        except ValueError:
            status_parts = {}
 
        sms_status = status_parts.get("sms", "0")
        whatsapp_status = status_parts.get("whatsapp", "0")
 
        if sms_status == "1" and whatsapp_status == "1":
            msg.status_display = "Delivered via SMS and WhatsApp"
        elif sms_status == "1":
            msg.status_display = "Delivered via SMS"
        elif whatsapp_status == "1":
            msg.status_display = "Delivered via WhatsApp"
        else:
            msg.status_display = "Not Delivered"
 
        recent_messages.append(msg)
 
    context = {
        'total_students': total_students,
        'messages_sent': messages_sent,
        'active_departments': active_departments,
        'delivery_rate': delivery_rate,
        'recent_messages': recent_messages,
    }
 
    return render(request, 'master/dashboard.html', context)
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import StudentRecord, SentMessage
from asgiref.sync import sync_to_async, async_to_sync
import asyncio
from twilio.rest import Client
from django.conf import settings
from functools import partial
from django.utils import timezone

# Async Twilio sender with separate tracking
async def send_twilio_message(to_number, body, send_sms, send_whatsapp):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    loop = asyncio.get_event_loop()
    result = {'sms': False, 'whatsapp': False}

    try:
        if send_whatsapp:
            await loop.run_in_executor(
                None,
                partial(
                    client.messages.create,
                    body=body,
                    from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
                    to=f'whatsapp:{to_number}'
                )
            )
            result['whatsapp'] = True
    except Exception as e:
        print(f"❌ WhatsApp failed for {to_number}: {e}")

    try:
        if send_sms:
            await loop.run_in_executor(
                None,
                partial(
                    client.messages.create,
                    body=body,
                    from_=settings.TWILIO_SMS_NUMBER,
                    to=to_number
                )
            )
            result['sms'] = True
    except Exception as e:
        print(f"❌ SMS failed for {to_number}: {e}")

    return result

# ORM helpers wrapped in sync_to_async
@sync_to_async
def get_guardians_queryset(department):
    if department == "All":
        return list(StudentRecord.objects.all())
    return list(StudentRecord.objects.filter(department=department))

@sync_to_async
def create_pending_message(guardian, subject, message_text, send_sms, send_whatsapp):
    status = "sms:0 whatsapp:0"  # Initially not sent
    return SentMessage.objects.create(
        subject=subject,
        message=message_text,
        send_sms=send_sms,
        send_whatsapp=send_whatsapp,
        department=guardian.department,
        status=status,
        student_name=guardian,
        guardian_phone_no=guardian.guardian_phone.strip()
    )

@sync_to_async
def update_message_status(message_obj, status):
    message_obj.status = status
    message_obj.sent_at = timezone.now()
    message_obj.save()

# View Function
def compose_message(request):
    departments = StudentRecord.objects.values_list('department', flat=True).distinct()
    departments = sorted(set(departments))
    selected_department = request.POST.get('department', '')

    if request.method == 'POST':
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        send_sms = 'sms' in request.POST
        send_whatsapp = 'whatsapp' in request.POST
        department = request.POST.get('department')

        async def send_all():
            guardians = await get_guardians_queryset(department)
            full_message = f"Subject: {subject}\n{message_text}"
            failed = 0

            for guardian in guardians:
                phone = guardian.guardian_phone.strip()
                number = f'+91{phone}'  # Update this format if needed

                # Save initial message as pending
                message_obj = await create_pending_message(
                    guardian, subject, message_text, send_sms, send_whatsapp
                )

                # Send messages via Twilio
                result = await send_twilio_message(number, full_message, send_sms, send_whatsapp)

                # Compose actual status string
                status = f"sms:{int(result['sms'])} whatsapp:{int(result['whatsapp'])}"
                await update_message_status(message_obj, status)

                if not result['sms'] and not result['whatsapp']:
                    print(f"❌ Failed to send to: {number}")
                    failed += 1
                else:
                    print(f"✅ Sent to: {number} | Status: {status}")

            return failed

        failed_count = async_to_sync(send_all)()

        if failed_count == 0:
            messages.success(request, "✅ All messages sent successfully.")
        else:
            messages.warning(request, f"⚠️ Sent with {failed_count} failures.")

        return redirect('compose_message')

    return render(request, 'master/compose_message.html', {
        'departments': departments,
        'selected_department': selected_department
    })




from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import SentMessage

@login_required
def message_history_view(request):
    channel_filter = request.GET.get('channel', '')
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')

    # Get all messages and apply basic filters
    messages = SentMessage.objects.all().order_by('-sent_at')

    if channel_filter == 'sms':
        messages = messages.filter(send_sms=True)
    elif channel_filter == 'whatsapp':
        messages = messages.filter(send_whatsapp=True)

    if department_filter:
        messages = messages.filter(department=department_filter)

    departments = SentMessage.objects.values_list('department', flat=True).distinct()

    # Enhance messages with readable status and channel
    filtered_messages = []
    for msg in messages:
        # Parse status like: "sms:1 whatsapp:0"
        status_parts = dict(part.split(":") for part in msg.status.split() if ":" in part)

        sms_status = status_parts.get("sms", "0")
        whatsapp_status = status_parts.get("whatsapp", "0")

        msg.sms_status_display = "Delivered" if sms_status == "1" else "Not Delivered"
        msg.whatsapp_status_display = "Delivered" if whatsapp_status == "1" else "Not Delivered"

        if sms_status == "1" and whatsapp_status == "1":
            msg.status_display = "Delivered via SMS and WhatsApp"
        elif sms_status == "1":
            msg.status_display = "Delivered via SMS"
        elif whatsapp_status == "1":
            msg.status_display = "Delivered via WhatsApp"
        else:
            msg.status_display = "Not Delivered"

        if msg.send_sms and msg.send_whatsapp:
            msg.sent_via = "SMS & WhatsApp"
        elif msg.send_sms:
            msg.sent_via = "SMS"
        elif msg.send_whatsapp:
            msg.sent_via = "WhatsApp"
        else:
            msg.sent_via = "-"

        # Apply status filter (after computing readable status)
        if not status_filter:
            filtered_messages.append(msg)
        elif status_filter == "delivered" and (
            msg.sms_status_display == "Delivered" or msg.whatsapp_status_display == "Delivered"
        ):
            filtered_messages.append(msg)
        elif status_filter in ["pending", "failed"] and (
            msg.sms_status_display == "Not Delivered" and msg.whatsapp_status_display == "Not Delivered"
        ):
            filtered_messages.append(msg)

    # Limit to 2000 messages
    filtered_messages = filtered_messages[:2000]

    # Apply pagination - 100 per page (20 pages max)
    paginator = Paginator(filtered_messages, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'master/message_history.html', {
        'page_obj': page_obj,
        'channel_filter': channel_filter,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'departments': departments,
    })


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from twilio.rest import Client
from .models import SentMessage


@login_required
def resend_message_view(request, message_id):
    message = get_object_or_404(SentMessage, id=message_id)

    to_number = f"+91{message.guardian_phone_no.strip()}"
    body = f"Subject: {message.subject}\n{message.message}"

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    result = {'sms': False, 'whatsapp': False}

    try:
        if message.send_whatsapp:
            client.messages.create(
                body=body,
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{to_number}"
            )
            result['whatsapp'] = True
    except Exception as e:
        print(f"WhatsApp resend failed: {e}")

    try:
        if message.send_sms:
            client.messages.create(
                body=body,
                from_=settings.TWILIO_SMS_NUMBER,
                to=to_number
            )
            result['sms'] = True
    except Exception as e:
        print(f"SMS resend failed: {e}")

    # Update status after resend
    message.status = f"sms:{int(result['sms'])} whatsapp:{int(result['whatsapp'])}"
    message.save()

    messages.success(request, "Message resent successfully.")
    return redirect('compose_message')

