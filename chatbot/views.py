from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
from datetime import datetime
from conference.models import AbstractSubmission, Participant, ScientificTheme


class NCPSChatbot:
    """AI-powered chatbot for NCPS 2025 using local Ollama (qwen3:4b)"""
    
    def __init__(self, is_admin=False):
        self.is_admin = is_admin
        self.ai_enabled = settings.CHATBOT_AI_ENABLED
        
        # Ollama Configuration
        self.ollama_url = settings.OLLAMA_API_ENDPOINT
        self.model = settings.OLLAMA_MODEL
        self.temperature = settings.OLLAMA_TEMPERATURE
        self.max_tokens = settings.OLLAMA_MAX_TOKENS
        self.timeout = settings.OLLAMA_TIMEOUT
        
        print(f"✅ AI Initialized: Ollama")
        print(f"   Model: {self.model}")
        print(f"   URL: {self.ollama_url}")
        print(f"   Timeout: {self.timeout}s")
        print(f"   Admin Mode: {self.is_admin}")
        
        self.knowledge_base = self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load NCPS 2025 conference knowledge base"""
        return {
            'conference': {
                'name': 'National Conference on Polar Sciences (NCPS) 2025',
                'dates': '16th-18th September, 2025',
                'venue': 'National Centre for Polar and Ocean Research, Goa, India',
                'organizer': 'National Centre for Polar and Ocean Research, Ministry of Earth Sciences, Government of India',
                'email': 'ncps2025@ncpor.gov.in',
                'participants': '250+ participants including 100+ young researchers',
            },
            'themes': [
                'Arctic Climate Change',
                'Antarctic Ice Dynamics',
                'Southern Ocean Research',
                'Himalayan Cryosphere',
                'Polar Technology',
                'Interdisciplinary Studies'
            ],
                        'abstract_submission': {
                'guidelines': 'Submit either an abstract text (250–500 words) OR upload a PDF file. Both cannot be submitted together.',
                'text_rules': 'Text abstracts must be between 250 and 500 words.',
                'pdf_rules': 'If submitting PDF, only Title + PDF upload is required.',
                'review_process': 'All abstracts will be peer-reviewed by the scientific committee',
                'deadline': 'Check the Important Dates section on the website',
            },

            'registration': {
                'process': 'Create an account, complete your profile, and submit registration form',
                'categories': 'Faculty/Scientist, Student, Industry Professional',
                'payment': 'Details will be provided after registration approval',
            },
            'presentation': {
                'oral': '15-minute presentation + 5-minute Q&A',
                'poster': 'A0 size (841×1189mm), portrait orientation',
            },
            'admin_help': {
                'dashboard': 'Access analytics, view registrations, manage abstracts from the admin dashboard',
                'abstracts': 'Review, approve, reject, or request revisions for submitted abstracts',
                'registrations': 'View all registrations, filter by status, theme, or institution',
                'analytics': 'View statistics on submissions, registrations, and themes',
                'export': 'Use the export buttons to download data as CSV files',
                'notifications': 'Send email notifications to participants through the notification system',
            }
        }
    
    def get_greeting(self):
        """Return context-aware greeting"""
        if self.is_admin:
            return "<strong>👋 Welcome, Admin! I'm Penguin</strong><br><br>Your NCPS 2025 AI assistant. I can help you manage abstracts, registrations, analytics, and administrative tasks. What would you like to do?"
        else:
            return "<strong>👋 Welcome! I'm Penguin</strong><br><br>Your intelligent assistant for NCPS 2025. I can help with:<br>• <a href='/register/' style='color: #3b82f6;'>Registration</a><br>• <a href='/dashboard/' style='color: #3b82f6;'>Abstract Submission</a><br>• Conference Information<br>• General Questions<br><br>What can I help you with?"
    
    def get_quick_replies(self):
        """Return context-aware quick reply options"""
        if self.is_admin:
            return [
                "How do I review abstracts?",
                "Show current statistics",
                "Export registration list",
                "Filter abstracts by theme",
                "How to manage themes?"
            ]
        else:
            return [
                "How to submit an abstract?",
                "Registration information",
                "Conference dates and venue",
                "What are the themes?",
                "Presentation guidelines"
            ]
    
    def get_real_time_stats(self):
        """Fetch real-time statistics from database"""
        try:
            total_registrations = Participant.objects.count()
            total_abstracts = AbstractSubmission.objects.count()
            pending_abstracts = AbstractSubmission.objects.filter(status='PENDING').count()
            approved_abstracts = AbstractSubmission.objects.filter(status='APPROVED').count()
            rejected_abstracts = AbstractSubmission.objects.filter(status='REJECTED').count()
            revision_abstracts = AbstractSubmission.objects.filter(status='REVISION').count()
            total_themes = ScientificTheme.objects.count()
            
            return {
                'total_registrations': total_registrations,
                'total_abstracts': total_abstracts,
                'pending_abstracts': pending_abstracts,
                'approved_abstracts': approved_abstracts,
                'rejected_abstracts': rejected_abstracts,
                'revision_abstracts': revision_abstracts,
                'total_themes': total_themes,
            }
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return None
    
    def generate_ai_response(self, user_message, page_context=''):
        """Generate response using local Ollama AI (qwen3:4b)"""
        try:
            print(f"🤖 Generating AI response...")
            print(f"📡 Calling Ollama with message: {user_message[:50]}...")
            
            kb = self.knowledge_base
            page_type = getattr(self, 'page_type', 'home')
            page_ctx = getattr(self, 'page_context', '')
            message_lower = user_message.lower()
            
            # Smart fallback check - bypass AI for specific questions that need accurate responses
            # 1. Form field questions
            if any(phrase in message_lower for phrase in ['fill here', 'what i have to fill', 'form fields', 'required fields']) and page_type != 'home':
                print(f"🎯 Using page-specific fallback for {page_type} page")
                return self.generate_response(user_message)
            
            # 2. Link/navigation requests - bypass AI to provide direct links
            if any(phrase in message_lower for phrase in ['link for', 'give me link', 'give me the link', 'give mw the link', 'go to', 'take me to', 'page link', 'url for']):
                print(f"🔗 Using fallback for link request")
                return self.generate_response(user_message)
            
            # 3. Password reset questions - bypass AI for accurate instructions
            if any(phrase in message_lower for phrase in ['reset password', 'forgot password', 'password reset', 'change password', 'recover password', 'lost password', 'how to reset']):
                print(f"🔐 Using fallback for password reset")
                return self.generate_response(user_message)
            
            # 4. Identity questions
            if any(phrase in message_lower for phrase in ['who are you', 'what is your name', 'introduce yourself']):
                print(f"👤 Using fallback for identity question")
                return self.generate_response(user_message)
            
            # 5. Page identification
            if any(phrase in message_lower for phrase in ['which page', 'what page', 'current page', 'where am i']):
                print(f"📍 Using fallback for page identification")
                return self.generate_response(user_message)
            
            # Build system prompt with conference context
            if self.is_admin:
                # Fetch real-time statistics for admin
                stats = self.get_real_time_stats()
                stats_text = ""
                if stats:
                    stats_text = f"""
CURRENT STATISTICS (Real-time from database):
- Total Registrations: {stats['total_registrations']}
- Total Abstracts: {stats['total_abstracts']}
- Pending Abstracts: {stats['pending_abstracts']}
- Approved Abstracts: {stats['approved_abstracts']}
- Rejected Abstracts: {stats['rejected_abstracts']}
- Revision Requested: {stats['revision_abstracts']}
- Active Themes: {stats['total_themes']}
"""
                
                system_prompt = f"""You are an AI assistant for NCPS 2025 administrative dashboard.

Help admins with:
- Managing abstract submissions (review, approve, reject, request revisions)
- Viewing registrations and filtering data
- Providing current statistics and numbers
- Exporting data to CSV
- Understanding the admin dashboard

Conference: {kb['conference']['name']}
Dates: {kb['conference']['dates']}
Themes: {', '.join(kb['themes'])}{stats_text}

IMPORTANT:
- When asked about statistics, numbers, counts, or "how many", provide the EXACT numbers from CURRENT STATISTICS above
- You have access to REAL-TIME data - use it!
- Automatic notifications are sent when you approve/reject abstracts (manual bulk notifications are NOT available)

RESPONSE FORMAT:
- Use <strong>HEADING</strong> for titles
- Use <br><br> between paragraphs (NOT double URLs or duplicates)
- Use • for bullet points
- Keep responses 2-3 short paragraphs
- NO DUPLICATES - each URL or info appears only ONCE

Be professional, concise, and actionable."""
            else:
                # Determine current page context
                page_context_info = ""
                if page_type == 'login':
                    page_context_info = "\n\nCURRENT PAGE: Login Page - User needs Username and Password to login."
                elif page_type == 'register':
                    page_context_info = "\n\nCURRENT PAGE: Registration Page - User needs to fill: Username, Email, Password, Confirm Password, First Name, Last Name, Organization/Institution, Designation."
                elif page_type == 'dashboard':
                    page_context_info = "\n\nCURRENT PAGE: User Dashboard - User can submit abstracts, view submissions, edit profile."
                elif page_type == 'abstract':
                    page_context_info = (
                        "\n\nCURRENT PAGE: Abstract Submission Form\n"
                        "- Title is mandatory\n"
                        "- User must submit EITHER abstract text (250–500 words) OR upload a PDF\n"
                        "- Both cannot be submitted together\n"
                        "- Theme selection is required"
                    )

                
                system_prompt = f"""You are Penguin, the NCPS 2025 Conference Assistant.

NCPS 2025 Conference Info:
Event: {kb['conference']['name']}
Dates: {kb['conference']['dates']}
Venue: {kb['conference']['venue']}
Email: {kb['conference']['email']}
Themes: {', '.join(kb['themes'])}{page_context_info}

GUIDELINES TO PROVIDE TO USERS:

Registration Guidelines:
- Create account with valid email, username, password
- Fill personal info: Name, Institution, Designation
- Complete profile after registration
- Login to access dashboard

Abstract Submission Guidelines:
- Submit EITHER abstract text (250–500 words) OR upload a PDF file
- Both cannot be submitted together
- Title is mandatory in all cases
- Theme selection is required
- PDF upload requires no abstract text
- Review process: {kb['abstract_submission']['review_process']}

Presentation Guidelines:
- Oral presentations: 15 min talk + 5 min Q&A
- Poster presentations: A0 size, portrait orientation
- Format assigned after acceptance
- Present during scheduled sessions

Password Reset Process:
- Go to Login Page → Click "Forgot Password?"
- Enter registered email → Check inbox for reset link
- Follow link to create new password
- If no email within 5 min, check spam folder

CRITICAL FORMATTING RULES:
1. ALWAYS use HTML tags: <strong>TEXT</strong> for bold, <br> for line breaks, <br><br> between paragraphs
2. NEVER use markdown (**text**, ##, *, etc.) - only HTML
3. Use • (bullet) character for lists, NOT asterisks or dashes
4. For links use: <a href='URL' style='color: #3b82f6;'>Link Text</a>

RESPONSE RULES:
1. ONLY when asked "who are you", "what is your name", "introduce yourself":
   - Say: "I am <strong>Penguin</strong>, your NCPS 2025 conference assistant. I can help with registration, abstracts, and conference information."

2. For ALL OTHER questions - Just answer the question directly WITHOUT introducing yourself

3. For OFF-TOPIC questions (e.g., "what is Google"):
   - Brief answer (1-2 sentences)
   - Add: "<br><br><em>Note: I'm primarily designed to assist with NCPS 2025. Ask me about registration, abstracts, or conference details!</em>"

4. For CONFERENCE questions - Provide detailed, step-by-step guidelines from the info above

5. When providing guidelines, be comprehensive and include all relevant steps

Keep responses helpful and detailed (3-5 paragraphs for guidelines). Use proper HTML formatting."""
            
            # Add page context if available
            page_info = ""
            if page_context:
                page_info = f"\n\nPAGE CONTEXT: {page_context}\nProvide specific help for THIS page."
            
            # Generate AI response
            full_prompt = f"{system_prompt}{page_info}\n\nUser Question: {user_message}\n\nAssistant:"
            
            print(f"🔍 Sending prompt to Ollama (length: {len(full_prompt)})")
            
            # Call Ollama API
            payload = {
                'model': self.model,
                'prompt': full_prompt,
                'stream': False,
                'temperature': self.temperature,
                'num_predict': self.max_tokens,
            }
            
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=self.timeout
            )
            
            print(f"📨 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '').strip()
                
                print(f"✅ AI response received (length: {len(ai_response)})")
                
                if ai_response:
                    # Clean up markdown formatting that AI might still use
                    # Remove markdown bold **text** and replace with <strong>
                    import re
                    ai_response = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', ai_response)
                    # Remove markdown headers ## and ###
                    ai_response = re.sub(r'#+\s*', '', ai_response)
                    # Replace markdown bullets * or - with •
                    ai_response = re.sub(r'^\s*[\*\-]\s+', '• ', ai_response, flags=re.MULTILINE)
                    
                    # Ensure HTML formatting for line breaks
                    if '<br>' not in ai_response and '\n\n' in ai_response:
                        ai_response = ai_response.replace('\n\n', '<br><br>')
                    if '<br>' not in ai_response and '\n' in ai_response:
                        ai_response = ai_response.replace('\n', '<br>')
                    
                    return ai_response
                else:
                    return self.generate_response(user_message)
            else:
                print(f"❌ Ollama error: HTTP {response.status_code}")
                return self.generate_response(user_message)
        
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect to Ollama at {self.ollama_url}")
            print(f"   Make sure Ollama is running: ollama serve")
            return self.generate_response(user_message)
        
        except Exception as e:
            print(f"❌ AI generation error: {str(e)}")
            return self.generate_response(user_message)
    
    def generate_response(self, user_message):
        """Fallback: Generate response using keywords"""
        message_lower = user_message.lower()
        kb = self.knowledge_base
        
        # Check for page-specific context questions FIRST
        page_type = getattr(self, 'page_type', 'home')
        if any(phrase in message_lower for phrase in ['fill here', 'what i have to fill', 'what do i fill', 'fill in', 'required fields', 'form fields']):
            if page_type == 'login':
                return "<strong>📝 Login Page</strong><br><br>To login, fill in:<br>• <strong>Username:</strong> Your registered email or username<br>• <strong>Password:</strong> Your account password<br><br>Don't have an account? <a href='/register/' style='color: #3b82f6; font-weight: bold;'>Register here</a>"
            elif page_type == 'register':
                return "<strong>📝 Registration Form Fields</strong><br><br><strong>Account Details:</strong><br>• <strong>Username</strong> - Choose unique username<br>• <strong>Email</strong> - Valid email address<br>• <strong>Password</strong> - Create secure password<br>• <strong>Confirm Password</strong> - Re-enter password<br><br><strong>Personal Info:</strong><br>• <strong>First Name & Last Name</strong><br>• <strong>Organization/Institution</strong><br>• <strong>Designation</strong> - Your role/position<br><br>Complete all steps to finish registration."
            elif page_type == 'abstract':
                return (
                    "<strong>📝 Abstract Submission Form</strong><br><br>"
                    "<strong>Required:</strong><br>"
                    "• <strong>Title</strong><br>"
                    "• <strong>Theme</strong><br><br>"
                    "<strong>Choose ONE method:</strong><br>"
                    "• Abstract text (250–500 words)<br>"
                    "• OR PDF upload<br><br>"
                    "<strong>Do NOT submit both together.</strong>"
                )
            elif page_type == 'dashboard':
                return "<strong>📝 Dashboard Features</strong><br><br>From here you can:<br>• <strong>Submit Abstract</strong> - Click 'Submit New Abstract'<br>• <strong>View Submissions</strong> - See status of your abstracts<br>• <strong>Edit Profile</strong> - Update your information<br>• <strong>Track Progress</strong> - Monitor review status"
        
        # Check for page identification questions
        if any(phrase in message_lower for phrase in ['which page', 'what page', 'current page', 'where am i']):
            if page_type == 'login':
                return "<strong>📍 Current Page</strong><br><br>You are on the <strong>Login Page</strong>.<br><br>This is where you enter your credentials to access the conference portal. Enter your username and password to continue."
            elif page_type == 'register':
                return "<strong>📍 Current Page</strong><br><br>You are on the <strong>Registration Page</strong>.<br><br>This is where you create a new account for NCPS 2025. Fill in the registration form with your details to get started."
            elif page_type == 'dashboard':
                return "<strong>📍 Current Page</strong><br><br>You are on your <strong>Dashboard</strong>.<br><br>This is your personal control center where you can submit abstracts, view your submissions, and manage your profile."
            elif page_type == 'abstract':
                return "<strong>📍 Current Page</strong><br><br>You are on the <strong>Abstract Submission Page</strong>.<br><br>This is where you submit your research abstract for the conference."
            else:
                return "<strong>📍 Current Page</strong><br><br>You are on the <strong>NCPS 2025 Home Page</strong>.<br><br>This is the main conference information page. You can navigate to Login, Registration, or explore conference details from here."
        
        # Check for identity/introduction questions
        if any(phrase in message_lower for phrase in ['who are you', 'what is your name', 'your name', 'introduce yourself', 'what are you']):
            return "<strong>👋 Hello! I'm Penguin</strong><br><br>Your intelligent assistant for <strong>NCPS 2025</strong> - the National Conference on Polar Sciences.<br><br><strong>I can help you with:</strong><br>• Registration and account setup<br>• Abstract submission guidelines<br>• Conference dates, venue, and schedules<br>• Scientific themes and topics<br>• General questions about NCPS<br><br>What would you like to know about the conference?"
        
        # Check for navigation/link requests
        if any(phrase in message_lower for phrase in ['login page link', 'link for login', 'login link', 'go to login', 'take me to login', 'login url']):
            return "<strong>🔗 Login Page</strong><br><br>You can access the login page here:<br><a href='/login/' style='color: #3b82f6; font-weight: bold; text-decoration: underline;'>→ Go to Login Page</a><br><br>Don't have an account yet? <a href='/register/' style='color: #3b82f6;'>Register here</a>"
        
        if any(phrase in message_lower for phrase in ['register page link', 'link for register', 'registration link', 'signup link', 'go to register', 'take me to register']):
            return "<strong>🔗 Registration Page</strong><br><br>Create your NCPS 2025 account:<br><a href='/register/' style='color: #3b82f6; font-weight: bold; text-decoration: underline;'>→ Go to Registration Page</a><br><br>Already have an account? <a href='/login/' style='color: #3b82f6;'>Login here</a>"
        
        if any(phrase in message_lower for phrase in ['dashboard link', 'go to dashboard', 'take me to dashboard', 'my dashboard']):
            return "<strong>🔗 Dashboard</strong><br><br>Access your dashboard:<br><a href='/dashboard/' style='color: #3b82f6; font-weight: bold; text-decoration: underline;'>→ Go to Dashboard</a><br><br><em>Note: You need to be logged in to access the dashboard.</em>"
        
        if any(phrase in message_lower for phrase in ['home page link', 'go to home', 'take me home', 'main page']):
            return "<strong>🔗 Home Page</strong><br><br>Return to the main page:<br><a href='/' style='color: #3b82f6; font-weight: bold; text-decoration: underline;'>→ Go to Home Page</a>"
        
        # Check for password reset questions
        if any(phrase in message_lower for phrase in ['reset password', 'forgot password', 'forgot my password', 'password reset', 'change password', 'recover password', 'lost password', 'how to reset', 'cant login', "can't login", 'cannot login']):
            return "<strong>🔐 Reset Your Password</strong><br><br><strong>Steps to reset your password:</strong><br><br>1. Go to the <a href='/login/' style='color: #3b82f6; font-weight: bold;'>Login Page</a><br>2. Click on <strong>'Forgot Password?'</strong> link<br>3. Enter your registered email address<br>4. Check your email for reset instructions<br>5. Click the reset link in the email<br>6. Create a new password<br><br><strong>Note:</strong> If you don't receive the email within 5 minutes, check your spam folder.<br><br>Need more help? Contact <a href='mailto:ncps2025@ncpor.gov.in' style='color: #3b82f6;'>ncps2025@ncpor.gov.in</a>"
        
        # Admin-specific responses
        if self.is_admin:
            if any(word in message_lower for word in ['review', 'approve', 'reject']):
                return (
                    "<strong>📋 Review Abstracts</strong><br><br>"
                    "Steps:<br>"
                    "1. Go to Admin Dashboard → Abstracts<br>"
                    "2. Click an abstract to view details<br>"
                    "3. Approve, Reject, or Request Revision<br>"
                    "4. Add admin comments<br>"
                    "5. Submit to notify the author"
                )

            elif any(word in message_lower for word in ['analytics', 'statistics']):
                return (
                    "<strong>📊 Analytics Dashboard</strong><br><br>"
                    "• Total registrations & abstracts<br>"
                    "• Theme-wise distribution<br>"
                    "• Submission trends<br>"
                    "• Status breakdown"
                )

            else:
                return (
                    "<strong>Admin Tools</strong><br><br>"
                    "I can help you manage abstracts, registrations, analytics, and exports."
                )
        
        # --------------------------------------------------
        # Public user responses (NON-ADMIN)
        # --------------------------------------------------
        if any(word in message_lower for word in ['submit', 'abstract', 'submission']):
            return (
                "<strong>📝 Abstract Submission</strong><br><br>"
                "<strong>Submission Rules (IMPORTANT):</strong><br>"
                "• Submit <strong>EITHER</strong> abstract text <strong>OR</strong> a PDF file<br>"
                "• <strong>Do NOT submit both together</strong><br><br>"

                "<strong>Text Abstract Option:</strong><br>"
                "• 250–500 words<br>"
                "• Enter text in the abstract field<br><br>"

                "<strong>PDF Upload Option:</strong><br>"
                "• Upload PDF file only<br>"
                "• Title is mandatory<br>"
                "• Abstract text can be empty<br><br>"

                "<strong>Steps:</strong><br>"
                "1. Login/Register<br>"
                "2. Go to Dashboard<br>"
                "3. Click <strong>Submit Abstract</strong><br>"
                "4. Choose ONE method<br>"
                "5. Submit for review"
            )

        elif any(word in message_lower for word in ['register', 'registration', 'sign up']):
            return (
                "<strong>📋 Register for NCPS 2025</strong><br><br>"
                "<strong>Required Fields:</strong><br>"
                "• Full Name<br>"
                "• Email Address<br>"
                "• Institution/Organization<br>"
                "• Select Category (Faculty/Student/Professional)<br>"
                "• Create Password<br><br>"
                "<strong>After Registration:</strong><br>"
                "• Complete your profile<br>"
                "• Submit registration<br>"
                "• Await approval<br><br>"
                "<a href='/register/' style='color: #3b82f6; font-weight: bold; text-decoration: underline;'>"
                "→ Register Now</a>"
            )
        elif any(word in message_lower for word in ['date', 'when', 'schedule']):
            return (
                f"<strong>📅 Conference Schedule</strong><br><br>"
                f"<strong>Dates:</strong> {kb['conference']['dates']}<br><br>"
                f"<strong>Venue:</strong><br>{kb['conference']['venue']}<br><br>"
                "Features:<br>"
                "• Keynote speeches<br>"
                "• Oral presentations<br>"
                "• Poster sessions<br>"
                "• Networking events<br><br>"
                "Detailed schedule coming soon!"
            )
        elif any(word in message_lower for word in ['theme', 'topic', 'subject', 'focus']):
            themes_list = '<br>'.join([f"• {t}" for t in kb['themes']])
            return (
                "<strong>🔬 Scientific Themes</strong><br><br>"
                f"{themes_list}<br><br>"
                "You can submit abstracts under any theme."
            )
        elif any(word in message_lower for word in ['presentation', 'oral', 'poster', 'format']):
            return (
                "<strong>🎤 Presentation Formats</strong><br><br>"
                "<strong>Oral Presentation:</strong><br>"
                "• 15 minutes presentation<br>"
                "• 5 minutes Q&A<br><br>"
                "<strong>Poster Presentation:</strong><br>"
                "• A0 size (841×1189mm)<br>"
                "• Portrait orientation<br><br>"
                "Format assigned after abstract acceptance."
            )
        elif any(word in message_lower for word in ['venue', 'location', 'where', 'address']):
            return (
                f"<strong>📍 Conference Venue</strong><br><br>"
                f"{kb['conference']['venue']}<br><br>"
                "• Located in Goa, India<br>"
                "• Accommodation info coming soon<br>"
                "• Travel guidelines for participants<br><br>"
                f"Contact: {kb['conference']['email']}"
            )
        elif any(word in message_lower for word in ['contact', 'email', 'help', 'support']):
            email_link = f"<a href='mailto:{kb['conference']['email']}' style='color: #3b82f6;'>{kb['conference']['email']}</a>"
            return (
                "<strong>📧 Get Help</strong><br><br>"
                f"Email: {email_link}<br><br>"
                "• Abstract queries<br>"
                "• Registration help<br>"
                "• Technical support"
            )
        elif any(word in message_lower for word in ['about', 'what is', 'ncps', 'conference info']):
            return (
                f"<strong>ℹ️ About NCPS 2025</strong><br><br>"
                f"{kb['conference']['name']}<br><br>"
                f"{kb['conference']['participants']}<br><br>"
                "<strong>Focus:</strong><br>"
                "• Interdisciplinary research<br>"
                "• Early-career researchers<br>"
                "• International collaboration"
            )
        else:
            return (
                "<strong>Welcome to NCPS 2025 Assistant!</strong><br><br>"
                "I can help you with:<br>"
                "• 📝 Abstract submission<br>"
                "• 📋 Registration<br>"
                "• 📅 Conference schedule<br>"
                "• 🔬 Scientific themes<br>"
                "• 🎤 Presentation guidelines<br><br>"
                "What would you like to know?"
            )
    
    def get_response(self, message, conversation_history=None):
        """Main method to get chatbot response"""
        print(f"🤖 get_response called. AI enabled: {self.ai_enabled}")
        if self.ai_enabled:
            print(f"📡 Using Ollama AI for message: {message[:50]}...")
            response = self.generate_ai_response(message)
        else:
            print(f"📚 Using keyword-based response")
            response = self.generate_response(message)
        
        return {
            'message': response,
            'timestamp': datetime.now().isoformat(),
            'quick_replies': self.get_quick_replies() if len(message.strip()) < 10 else []
        }


@csrf_exempt
def chatbot_init(request):
    """Initialize chatbot with greeting and quick replies"""
    try:
        is_admin = request.user.is_staff if request.user.is_authenticated else False
        chatbot = NCPSChatbot(is_admin=is_admin)
        
        return JsonResponse({
            'greeting': chatbot.get_greeting(),
            'quick_replies': chatbot.get_quick_replies(),
            'is_admin': is_admin
        })
    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            'greeting': 'Welcome to NCPS 2025!',
            'quick_replies': [],
            'is_admin': False
        })


@csrf_exempt
def chatbot_message(request):
    """API endpoint to handle chatbot messages"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        is_admin = data.get('is_admin', False)
        page_context = data.get('page_context', '')
        page_type = data.get('page_type', 'home')
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Initialize chatbot
        chatbot = NCPSChatbot(is_admin=is_admin)
        chatbot.page_context = page_context
        chatbot.page_type = page_type
        
        # Handle special commands
        if user_message.lower() == '/start':
            response = {
                'message': chatbot.get_greeting(),
                'quick_replies': chatbot.get_quick_replies(),
                'timestamp': datetime.now().isoformat()
            }
        elif user_message.lower() in ['hello', 'hi', 'hey']:
            response = {
                'message': 'Hello! How can I assist you with NCPS 2025 today?',
                'quick_replies': chatbot.get_quick_replies(),
                'timestamp': datetime.now().isoformat()
            }
        else:
            response = chatbot.get_response(user_message)
        
        return JsonResponse(response)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
