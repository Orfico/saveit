# SaveIt - Personal Finance Manager

A modern Django web application for managing personal finances with transaction tracking, recurring transactions, and insightful analytics.

# 💰 SaveIt - Personal Finance Manager

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-6.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Tests](https://github.com/Orfico/saveit/actions/workflows/ci-tests.yml/badge.svg)
![Security](https://img.shields.io/badge/Security-Grade%20A-brightgreen)
![HTTPS](https://img.shields.io/badge/HTTPS-Enforced-blue)
![CSP](https://img.shields.io/badge/CSP-Enabled-success)

## ✨ Features

- 📊 **Dashboard** with financial overview and statistics
- 💸 **Transaction Management** - Track income and expenses
- 🔄 **Recurring Transactions** - Automatic monthly transaction generation
- 📱 **Mobile-First Design** - Optimized UX for mobile devices
- 🏷️ **Categories** - Organize transactions with custom categories
- 🔍 **Filters & Search** - Find transactions easily
- 👤 **User Authentication** - Secure login and registration
- 🔐 **Password Reset** - Email-based password recovery
- 📈 **Analytics** - Visualize your financial data
- 🛡️ **Enterprise-Grade Security** - CSP, HSTS, secure cookies, HTTPS enforced

## 🚀 Live Demo

Visit the live application: [https://saveit-v32r.onrender.com](https://saveit-v32r.onrender.com)

## 🛠️ Tech Stack

- **Backend:** Django 6.0, Python 3.12
- **Database:** PostgreSQL (Production: Supabase), SQLite (Development)
- **Frontend:** Tailwind CSS, Lucide Icons
- **Deployment:** Render
- **CI/CD:** GitHub Actions
- **Email:** Resend API
- **Security:** 
  - CSP (Content Security Policy)
  - HSTS (HTTP Strict Transport Security)
  - SRI (Subresource Integrity)
  - Secure cookies (HttpOnly, Secure, SameSite)
  - HTTPS enforced

## 🔐 Security

SaveIt implements industry-standard security practices to protect user data and prevent common web vulnerabilities:

### **Application Security**
- ✅ **Content Security Policy (CSP)** - Prevents XSS attacks by controlling resource loading
- ✅ **CSRF Protection** - Django's built-in Cross-Site Request Forgery protection
- ✅ **SQL Injection Prevention** - Django ORM with parameterized queries
- ✅ **Secure Password Storage** - PBKDF2 algorithm with SHA256 hash
- ✅ **Password Validation** - Enforces strong passwords (length, complexity, common passwords check)

### **Transport Security**
- ✅ **HTTPS Enforced** - Automatic redirect from HTTP to HTTPS in production
- ✅ **HSTS (HTTP Strict Transport Security)** - 1-year policy with subdomain inclusion
- ✅ **Secure Cookies** - HttpOnly, Secure, and SameSite attributes enabled
- ✅ **TLS/SSL** - All data encrypted in transit

### **Infrastructure Security**
- ✅ **Environment Variables** - All secrets stored as environment variables (never in code)
- ✅ **Subresource Integrity (SRI)** - External scripts verified with cryptographic hashes
- ✅ **X-Frame-Options** - Clickjacking protection (DENY policy)
- ✅ **X-Content-Type-Options** - MIME-sniffing protection

### **Security Headers**
```http
Content-Security-Policy: default-src 'self'; script-src 'self' https://unpkg.com ...
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

### **Security Score**
- 🏆 **Mozilla Observatory: Grade B** (75/100)
- 🏆 **SecurityHeaders.com: Grade A**
- 🏆 **SSL Labs: A+**

### **Authentication & Authorization**
- ✅ Session-based authentication with secure cookies
- ✅ Login required for all financial data
- ✅ User-scoped queries (users can only access their own data)
- ✅ Email-based password reset with time-limited tokens

### **Database Security**
- ✅ Row-level access control via Django ORM
- ✅ PostgreSQL with SSL in production (Supabase)
- ✅ No direct database access from frontend
- ✅ Prepared statements prevent SQL injection

### **Development Best Practices**
- ✅ Separate development and production configurations
- ✅ Debug mode disabled in production
- ✅ Automated security checks via `python manage.py check --deploy`
- ✅ Regular dependency updates
- ✅ No hardcoded credentials
- ✅ `.env` files excluded from version control

## 📦 Installation

### Prerequisites

- Python 3.12+
- PostgreSQL (optional for local development)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Orfico/saveit.git
cd saveit
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

Create a `.env` file in the root directory with the following variables:
```env
# Django Settings
SECRET_KEY=your-secret-key-here-generate-one
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (optional - uses SQLite by default)
# DATABASE_URL=postgresql://user:password@localhost:5432/saveit_db

# Email Configuration (optional for development)
# RESEND_API_KEY=your-resend-api-key
# DEFAULT_FROM_EMAIL=SaveIt <noreply@yourdomain.com>
```

**⚠️ IMPORTANT:** Never commit `.env` to Git! It's already in `.gitignore`.

**Generate a SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Load Initial Data (Optional)

Create some default categories:
```bash
python manage.py shell
```
```python
from core.models import Category
from django.contrib.auth.models import User

user = User.objects.first()  # Or your superuser

# Create default categories
categories = [
    {'name': 'Salary', 'type': 'income', 'color': '#10B981'},
    {'name': 'Food', 'type': 'expense', 'color': '#EF4444'},
    {'name': 'Transport', 'type': 'expense', 'color': '#F59E0B'},
    {'name': 'Entertainment', 'type': 'expense', 'color': '#8B5CF6'},
    {'name': 'Rent', 'type': 'expense', 'color': '#EC4899'},
]

for cat in categories:
    Category.objects.create(
        name=cat['name'],
        type=cat['type'],
        user=user,
        scope='personal',
        color=cat['color']
    )
```

### 8. Run Development Server
```bash
python manage.py runserver
```

Visit: `http://localhost:8000`

## 🧪 Running Tests
```bash
# Run all tests
python manage.py test

# Run with coverage
pip install coverage
coverage run --source='core' manage.py test
coverage report
coverage html  # Generate HTML report in htmlcov/
```

## 🔄 Recurring Transactions

### Manual Generation
```bash
# Generate recurring transactions for current month
python manage.py generate_recurring_transactions

# Dry-run mode (preview without creating)
python manage.py generate_recurring_transactions --dry-run
```

### Automatic Generation

The project uses GitHub Actions to automatically generate recurring transactions on the 1st of each month. See `.github/workflows/recurring-transactions.yml`.

## 📁 Project Structure
```
saveit/
├── core/                          # Main Django app
│   ├── management/
│   │   └── commands/
│   │       └── generate_recurring_transactions.py
│   ├── migrations/
│   ├── templates/
│   │   ├── base.html
│   │   └── core/
│   │       ├── dashboard.html
│   │       ├── transaction_list.html
│   │       ├── transaction_form.html
│   │       └── ...
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_forms.py
│   │   └── test_commands.py
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── finance_app/                   # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── .github/
│   └── workflows/
│       ├── ci-tests.yml          # Automated testing
│       └── recurring-transactions.yml
├── .gitignore
├── requirements.txt
├── manage.py
└── README.md
```

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Django secret key |
| `DEBUG` | No | `False` | Debug mode (use `True` for development) |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `RESEND_API_KEY` | No | Console | Resend API key for emails |
| `DEFAULT_FROM_EMAIL` | No | - | From email address |

## 🚢 Deployment

### Render.com

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure environment variables in Render Dashboard:
```bash
SECRET_KEY=<generate-with-secrets.token_urlsafe(50)>
DEBUG=False
ALLOWED_HOSTS=your-app.onrender.com
DATABASE_URL=<supabase-postgresql-url>
RESEND_API_KEY=<your-resend-key>
```

4. Render will automatically deploy on push to `main`

**Build Command:**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start Command:**
```bash
gunicorn finance_app.wsgi:application
```

### Security Checklist for Production

- ✅ `DEBUG=False` in environment variables
- ✅ `SECRET_KEY` is strong (50+ characters, random)
- ✅ `ALLOWED_HOSTS` includes only your domain
- ✅ Database uses SSL connection (Supabase)
- ✅ HTTPS enforced (automatic on Render)
- ✅ Environment variables never committed to Git

### Database (Supabase)

1. Create a PostgreSQL database on Supabase
2. Copy the connection string
3. Add to Render environment variables as `DATABASE_URL`

## 📊 CI/CD

The project uses GitHub Actions for:

- **Automated Testing** - Runs tests on every push
- **Code Coverage** - Tracks test coverage
- **Recurring Transactions** - Generates transactions monthly

See `.github/workflows/` for workflow configurations.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🧹 Code Quality
```bash
# Run tests
python manage.py test

# Check for migrations
python manage.py makemigrations --check --dry-run

# Format code (optional)
black core/
flake8 core/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Luca Brambilla**
- GitHub: [@Orfico](https://github.com/Orfico)

## 🙏 Acknowledgments

- Django framework
- Tailwind CSS
- Lucide Icons
- Render for hosting
- Supabase for database

## 📧 Support

For support, open an issue on GitHub.

---