# SaveIt - Personal Finance Manager

A modern Django web application for managing personal finances with transaction tracking, recurring transactions, loyalty cards, and insightful analytics.

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
- 🎫 **Loyalty Cards** - Store and manage digital loyalty cards with barcodes
- 📱 **Mobile-First Design** - Optimized UX for mobile devices
- 🏷️ **Categories** - Organize transactions with custom categories
- 🔍 **Filters & Search** - Find transactions easily
- 👤 **User Authentication** - Secure login and registration
- 🔐 **Password Reset** - Email-based password recovery
- 📈 **Analytics** - Visualize your financial data
- ☁️ **Cloud Storage** - Barcode images stored on Supabase S3
- 🛡️ **Enterprise-Grade Security** - CSP, HSTS, secure cookies, HTTPS enforced

## 🚀 Live Demo

Visit the live application: [https://saveit-v32r.onrender.com](https://saveit-v32r.onrender.com)

## 🛠️ Tech Stack

- **Backend:** Django 6.0, Python 3.12
- **Database:** PostgreSQL (Production: Supabase), SQLite (Development)
- **Storage:** Supabase Storage (S3-compatible) with boto3
- **Frontend:** Tailwind CSS, Lucide Icons
- **Barcode Generation:** python-barcode, Pillow
- **Deployment:** Render (512MB RAM, 1 worker gunicorn)
- **CI/CD:** GitHub Actions
- **Email:** Resend API
- **Security:** 
  - CSP (Content Security Policy)
  - HSTS (HTTP Strict Transport Security)
  - SRI (Subresource Integrity)
  - Secure cookies (HttpOnly, Secure, SameSite)
  - HTTPS enforced

## 🎫 Loyalty Cards Feature

SaveIt includes a powerful loyalty cards manager that allows you to:

- **Store digital cards** - Keep all your loyalty cards in one place
- **Auto-generate barcodes** - Automatically creates barcodes from card numbers
- **Multiple formats** - Supports EAN-13, EAN-8, UPC-A, Code128, and ITF
- **Mobile-friendly** - Large, full-screen barcode display optimized for scanners
- **Cloud storage** - Barcode images stored on Supabase Storage (S3-compatible)
- **Download & Share** - Save or share barcode images
- **Print ready** - Optimized print view

### Supported Barcode Types

| Type | Example | Auto-detected |
|------|---------|---------------|
| EAN-13 | 4006381333931 | ✅ 13 digits |
| EAN-8 | 96385074 | ✅ 8 digits |
| UPC-A | 012345678905 | ✅ 12 digits |
| Code128 | ABC-1234567 | ✅ Default |
| ITF | 00123456 | ✅ Even-length numbers |

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

### **Database & Storage Security**
- ✅ Row-level access control via Django ORM
- ✅ PostgreSQL with SSL in production (Supabase)
- ✅ S3-compatible storage with access keys (Supabase Storage)
- ✅ No direct database access from frontend
- ✅ Prepared statements prevent SQL injection
- ✅ Public barcode images (non-sensitive data only)

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

# Supabase Storage (for loyalty card barcodes in production)
USE_S3=False  # Set to True in production
AWS_ACCESS_KEY_ID=your-supabase-s3-access-key
AWS_SECRET_ACCESS_KEY=your-supabase-s3-secret-key
AWS_STORAGE_BUCKET_NAME=media
AWS_S3_ENDPOINT_URL=https://your-project.storage.supabase.co/storage/v1/s3
AWS_S3_REGION_NAME=eu-west-1

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

### 7. Run Development Server
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
├── .github/
│   └── workflows/
│       ├── ci-tests.yml                # Automated testing on push
│       └── recurring-transactions.yml  # Monthly recurring transactions generation
├── core/                               # Main Django app
│   ├── management/
│   │   └── commands/
│   │       └── generate_recurring_transactions.py
│   ├── migrations/                     # Database migrations
│   ├── static/
│   │   └── core/
│   │       ├── css/
│   │       │   └── dashboard.css
│   │       └── js/
│   │           ├── utils.js
│   │           ├── dashboard.js
│   │           ├── loyalty_cards.js   # Loyalty cards management
│   │           └── loyalty_card_detail.js
│   ├── templates/
│   │   ├── base.html
│   │   └── core/
│   │       ├── dashboard.html
│   │       ├── transaction_list.html
│   │       ├── transaction_form.html
│   │       ├── category_list.html
│   │       ├── loyalty_cards_list.html      # NEW
│   │       ├── loyalty_card_detail.html     # NEW
│   │       ├── login.html
│   │       ├── register.html
│   │       └── password_reset/
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_forms.py
│   │   ├── test_loyalty_cards.py      # NEW
│   │   └── test_commands.py
│   ├── utils/
│   │   └── barcode_generator.py       # NEW - Barcode generation logic
│   ├── models.py                      # Includes LoyaltyCard model
│   ├── views.py                       # Includes loyalty card views
│   └── urls.py
├── finance_app/
│   ├── settings.py                    # S3 storage configuration
│   ├── urls.py
│   └── wsgi.py
├── build.sh                           # Render build script
├── start.sh                           # Render start script (migrations + gunicorn)
├── gunicorn_config.py                 # Gunicorn configuration (1 worker)
├── requirements.txt                   # Python dependencies
└── README.md
```

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Django secret key |
| `DEBUG` | No | `False` | Debug mode (use `True` for development) |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `USE_S3` | No | `False` | Enable Supabase S3 storage |
| `AWS_ACCESS_KEY_ID` | Yes (prod) | - | Supabase S3 access key |
| `AWS_SECRET_ACCESS_KEY` | Yes (prod) | - | Supabase S3 secret key |
| `AWS_STORAGE_BUCKET_NAME` | No | `media` | S3 bucket name |
| `AWS_S3_ENDPOINT_URL` | Yes (prod) | - | Supabase S3 endpoint |
| `AWS_S3_REGION_NAME` | No | `eu-west-1` | S3 region |
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
USE_S3=True
AWS_ACCESS_KEY_ID=<supabase-s3-access-key>
AWS_SECRET_ACCESS_KEY=<supabase-s3-secret-key>
AWS_STORAGE_BUCKET_NAME=media
AWS_S3_ENDPOINT_URL=https://your-project.storage.supabase.co/storage/v1/s3
AWS_S3_REGION_NAME=eu-west-1
RESEND_API_KEY=<your-resend-key>
```

4. Render will automatically deploy on push to `main`

**Build Command:**
```bash
./build.sh
```

**Start Command:**
```bash
./start.sh
```

### Supabase Setup

#### 1. **Database (PostgreSQL)**
1. Create a project on Supabase
2. Go to **Settings → Database**
3. Copy the **Connection String** (Transaction pooler mode)
4. Add to Render as `DATABASE_URL`

#### 2. **Storage (S3-compatible)**
1. Go to **Storage** in Supabase dashboard
2. Create a bucket named `media` (public)
3. Go to **Settings → Storage**
4. Enable **S3 Access**
5. Generate access keys
6. Add to Render:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_S3_ENDPOINT_URL` (from Supabase Storage settings)

### Memory Optimization (Render Free Tier)

The app is optimized for Render's free tier (512MB RAM):

- **1 gunicorn worker** (instead of 2+)
- **Reduced logging** (WARNING level, no boto3 DEBUG)
- **120s timeout** for slow requests
- **Migrations run on startup** (not during build)

## 📊 CI/CD

The project uses GitHub Actions for:

- **Automated Testing** - Runs tests on every push
- **Code Coverage** - Tracks test coverage (95%+)
- **Recurring Transactions** - Generates transactions monthly

See `.github/workflows/` for workflow configurations.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Luca Brambilla**
- GitHub: [@Orfico](https://github.com/Orfico)

## 🙏 Acknowledgments

- Django framework
- Tailwind CSS & Lucide Icons
- Render for hosting
- Supabase for database & storage
- python-barcode for barcode generation

## 📧 Support

For support, open an issue on GitHub.

---