import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse

from .models import Todo, Category, UserProfile
from .forms import RegisterForm, LoginForm, TodoForm, CategoryForm, UserProfileForm


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


# def register_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')
#     if request.method == 'POST':
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             UserProfile.objects.create(user=user)
#             Category.objects.create(user=user, name='Work', color='#4f46e5')
#             Category.objects.create(user=user, name='Personal', color='#10b981')
#             Category.objects.create(user=user, name='Shopping', color='#f59e0b')
#             login(request, user)
#             messages.success(request, f"Welcome, {user.first_name or user.username}! Your account is ready.")
#             return redirect('dashboard')
#         else:
#             messages.error(request, "Please fix the errors below.")
#     else:
#         form = RegisterForm()
#     return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def dashboard(request):
    todos = Todo.objects.filter(user=request.user)

    filter_status = request.GET.get('status', 'all')
    filter_priority = request.GET.get('priority', '')
    filter_category = request.GET.get('category', '')
    search_query = request.GET.get('q', '')

    if filter_status == 'active':
        todos = todos.filter(is_completed=False)
    elif filter_status == 'completed':
        todos = todos.filter(is_completed=True)
    elif filter_status == 'overdue':
        todos = todos.filter(is_completed=False, due_date__lt=timezone.now().date())

    if filter_priority:
        todos = todos.filter(priority=filter_priority)
    if filter_category:
        todos = todos.filter(category__id=filter_category)
    if search_query:
        todos = todos.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))

    all_todos = Todo.objects.filter(user=request.user)
    total = all_todos.count()
    completed = all_todos.filter(is_completed=True).count()
    active = all_todos.filter(is_completed=False).count()
    overdue = all_todos.filter(is_completed=False, due_date__lt=timezone.now().date()).count()

    todo_form = TodoForm(user=request.user)
    category_form = CategoryForm()
    categories = Category.objects.filter(user=request.user)

    # Build JSON for JS countdowns / notifications
    todos_list = list(todos)
    todos_json = json.dumps([
        {
            'id': t.id,
            'title': t.title,
            'deadline_ms': t.deadline_ts(),
            'is_completed': t.is_completed,
        }
        for t in todos_list
    ])

    context = {
        'todos': todos_list,
        'todos_json': todos_json,
        'todo_form': todo_form,
        'category_form': category_form,
        'categories': categories,
        'filter_status': filter_status,
        'filter_priority': filter_priority,
        'filter_category': filter_category,
        'search_query': search_query,
        'stats': {
            'total': total,
            'completed': completed,
            'active': active,
            'overdue': overdue,
            'completion_rate': round((completed / total * 100) if total > 0 else 0),
        },
        'today': timezone.now().date(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def add_todo(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'todo')
        if form_type == 'category':
            cat_form = CategoryForm(request.POST)
            if cat_form.is_valid():
                cat = cat_form.save(commit=False)
                cat.user = request.user
                cat.save()
                messages.success(request, f'Category "{cat.name}" created!')
            else:
                messages.error(request, "Could not create category.")
        else:
            form = TodoForm(request.user, request.POST)
            if form.is_valid():
                todo = form.save(commit=False)
                todo.user = request.user
                todo.save()
                messages.success(request, f'Task "{todo.title}" added!')
            else:
                messages.error(request, "Could not add task. Check the form.")
    return redirect('dashboard')


@login_required
def edit_todo(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TodoForm(request.user, request.POST, instance=todo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Task "{todo.title}" updated!')
            return redirect('dashboard')
    else:
        form = TodoForm(request.user, instance=todo)
    return render(request, 'edit_todo.html', {'form': form, 'todo': todo})


@login_required
def delete_todo(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    if request.method == 'POST':
        title = todo.title
        todo.delete()
        messages.success(request, f'Task "{title}" deleted.')
    return redirect('dashboard')


@login_required
def toggle_todo(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    todo.is_completed = not todo.is_completed
    todo.save()
    status = "completed" if todo.is_completed else "marked as active"
    messages.success(request, f'"{todo.title}" {status}.')
    return redirect('dashboard')


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    todos = Todo.objects.filter(user=request.user)
    categories = Category.objects.filter(user=request.user).annotate(todo_count=Count('todos'))
    context = {
        'profile': profile_obj,
        'categories': categories,
        'total_todos': todos.count(),
        'completed_todos': todos.filter(is_completed=True).count(),
    }
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile_obj)
        if form.is_valid():
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile_obj, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })
    return render(request, 'edit_profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'
    return render(request, 'change_password.html', {'form': form})


# ─── API: polling endpoint for JS push notification checks ───────────────────

# ...existing imports...
from django.core.mail import send_mail  # Import send_mail

from django.core.mail import send_mail
from django.contrib import messages

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            Category.objects.create(user=user, name='Work', color='#4f46e5')
            Category.objects.create(user=user, name='Personal', color='#10b981')
            Category.objects.create(user=user, name='Shopping', color='#f59e0b')
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name or user.username}! Your account is ready.")
            return redirect('dashboard')
            # Send welcome email
            subject = "Welcome to TodoProject!"
            message = f"Hi {user.first_name or user.username},\n\nThank you for registering at TodoProject. Start organizing your tasks today!"
            from_email = "noreply@todoapp.local"
            recipient_list = [user.email]
            try:
                send_mail(subject, message, from_email, recipient_list)
            except Exception as e:
                messages.error(request, "Could not send welcome email. Please check your email configuration.")
                # Log the error for debugging
                print(f"Email error: {e}")

        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

@login_required
def api_upcoming_deadlines(request):
    """
    Returns todos with deadlines in the next 24 hours (not completed).
    Sends email reminders for upcoming deadlines.
    """
    now = timezone.now()
    soon = now + timezone.timedelta(hours=24)
    todos = Todo.objects.filter(
        user=request.user,
        is_completed=False,
        due_datetime__isnull=False,
        due_datetime__lte=soon,
    ).order_by('due_datetime')

    data = []
    for t in todos:
        secs = (t.due_datetime - now).total_seconds()
        data.append({
            'id': t.id,
            'title': t.title,
            'seconds_left': int(secs),
            'overdue': secs < 0,
        })

        # Send email reminder for each task
        subject = f"Reminder: Upcoming Deadline for '{t.title}'"
        message = f"Hi {request.user.first_name or request.user.username},\n\nYour task '{t.title}' is due soon. Please make sure to complete it on time!"
        from_email = "muafelix79@gmail.com"  # Replace with your email
        recipient_list = [request.user.email]
        try:
            send_mail(subject, message, from_email, recipient_list)
        except Exception as e:
            messages.error(request, f"Could not send reminder email for task '{t.title}'. Please check your email configuration.")

    return JsonResponse({'todos': data})