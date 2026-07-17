"""
VideoForge Pro - Bilingual Translation System (Arabic/English)
"""
from flask import request, session, g, redirect
import os

TRANSLATIONS = {
    # Navbar
    "nav_home": {"ar": "الرئيسية", "en": "Home"},
    "nav_how": {"ar": "كيف يعمل", "en": "How It Works"},
    "nav_create": {"ar": "إنشاء فيديو", "en": "Create Video"},
    "nav_gallery": {"ar": "المعرض", "en": "Gallery"},
    "nav_admin": {"ar": "لوحة التحكم", "en": "Dashboard"},
    "nav_contact": {"ar": "اتصل بنا", "en": "Contact"},

    # Hero
    "hero_badge": {"ar": "🚀 بتقنية Wav2Lip + الذكاء الاصطناعي", "en": "🚀 Powered by Wav2Lip + AI"},
    "hero_title_1": {"ar": "حوّل أي صورة إلى", "en": "Turn any photo into an"},
    "hero_title_2": {"ar": "فيديو ناطق", "en": "AI Talking Video"},
    "hero_subtitle": {"ar": "تقنية Wav2Lip المتطورة تحرك الشفاه بتزامن تام مع الصوت، وكأن الشخص الحقيقي يتحدث. كل ما تحتاجه صورة واحدة + نص.", "en": "Advanced Wav2Lip technology moves lips in perfect sync with audio, as if the real person is speaking. All you need is one photo + text."},
    "hero_btn_start": {"ar": "🎬 ابدأ الإنشاء مجاناً", "en": "🎬 Start Creating Free"},
    "hero_btn_how": {"ar": "💡 كيف يعمل؟", "en": "💡 How It Works?"},

    # How It Works
    "how_title": {"ar": "كيف يعمل النظام؟", "en": "How It Works?"},
    "how_subtitle": {"ar": "أربع خطوات بسيطة لإنشاء فيديو ناطق احترافي", "en": "Four simple steps to create a professional talking video"},
    "how_step1_title": {"ar": "ارفع صورة", "en": "Upload Photo"},
    "how_step1_desc": {"ar": "صورة واضحة للوجه المراد تحريكه - PNG, JPG, WebP", "en": "A clear face photo - PNG, JPG, WebP"},
    "how_step2_title": {"ar": "أضف الصوت", "en": "Add Audio"},
    "how_step2_desc": {"ar": "ارفع ملف صوتي أو اكتب نصاً وسيحوله النظام لكلام طبيعي", "en": "Upload audio file or type text, AI converts to natural speech"},
    "how_step3_title": {"ar": "اختر الطريقة", "en": "Choose Method"},
    "how_step3_desc": {"ar": "معالجة محلية Wav2Lip أو عبر API سحابي sync.so", "en": "Local Wav2Lip processing or cloud sync.so API"},
    "how_step4_title": {"ar": "حمّل النتيجة", "en": "Download Result"},
    "how_step4_desc": {"ar": "فيديو ناطق بجودة HD جاهز للنشر على يوتيوب، تيك توك، انستغرام", "en": "HD talking video ready for YouTube, TikTok, Instagram"},

    # Features
    "features_title": {"ar": "مميزات VideoForge Pro", "en": "VideoForge Pro Features"},
    "features_subtitle": {"ar": "أفضل تقنية Wav2Lip لتحريك الشفاه بدقة", "en": "Best Wav2Lip technology for precise lip-sync"},
    "feature1_title": {"ar": "تحريك شفاه دقيق", "en": "Precise Lip-Sync"},
    "feature1_desc": {"ar": "تقنية Wav2Lip المتطورة تحرك الشفاه بتزامن تام مع الصوت، وكأن الشخص الحقيقي يتحدث.", "en": "Advanced Wav2Lip moves lips in perfect sync with audio, as if the real person is speaking."},
    "feature2_title": {"ar": "تحويل النص إلى كلام", "en": "Text-to-Speech"},
    "feature2_desc": {"ar": "أكثر من 100 صوت طبيعي بالعربية والإنجليزية والعديد من اللغات باستخدام Edge TTS.", "en": "100+ natural voices in Arabic, English and many languages using Edge TTS."},
    "feature3_title": {"ar": "سحابي أو محلي", "en": "Cloud or Local"},
    "feature3_desc": {"ar": "اختر بين المعالجة المحلية أو عبر API سحابي للحصول على نتائج أسرع وجودة أعلى.", "en": "Choose between local processing or cloud API for faster results and higher quality."},
    "feature4_title": {"ar": "أي صورة", "en": "Any Photo"},
    "feature4_desc": {"ar": "استخدم أي صورة وجه واضحة واحصل على فيديو ناطق فوري.", "en": "Use any clear face photo and get an instant talking video."},
    "feature5_title": {"ar": "تصدير بجودة عالية", "en": "HD Export"},
    "feature5_desc": {"ar": "الفيديوهات النهائية بجودة HD قابلة للتحميل والنشر على المنصات.", "en": "HD quality videos ready for download and publishing on all platforms."},
    "feature6_title": {"ar": "صوت طبيعي", "en": "Natural Voice"},
    "feature6_desc": {"ar": "أصوات ذكية طبيعية من Microsoft Edge TTS مع دعم النبرة والسرعة.", "en": "Natural AI voices from Microsoft Edge TTS with tone and speed control."},

    # Creator
    "creator_title": {"ar": "اصنع فيديو الآن", "en": "Create Video Now"},
    "creator_subtitle": {"ar": "اختر صورة + صوت أو نص ← فيديو ناطق خلال ثوانٍ", "en": "Photo + Audio or Text → Talking Video in seconds"},
    "creator_image_label": {"ar": "الصورة (الوجه)", "en": "Photo (Face)"},
    "creator_image_placeholder": {"ar": "اختر صورة للوجه", "en": "Choose a face photo"},
    "creator_image_hint": {"ar": "PNG, JPG, WebP - يفضل صورة واضحة للوجه", "en": "PNG, JPG, WebP - clear face photo preferred"},
    "creator_audio_label": {"ar": "الصوت", "en": "Audio"},
    "creator_audio_upload": {"ar": "رفع ملف صوتي", "en": "Upload Audio"},
    "creator_audio_text": {"ar": "كتابة نص (TTS)", "en": "Type Text (TTS)"},
    "creator_audio_placeholder": {"ar": "اختر ملف صوتي", "en": "Choose audio file"},
    "creator_audio_hint": {"ar": "MP3, WAV, M4A", "en": "MP3, WAV, M4A"},
    "creator_text_placeholder": {"ar": "اكتب النص الذي تريد أن يتحدث به الفيديو...", "en": "Type the text for the video to speak..."},
    "creator_auto": {"ar": "🔄 تلقائي", "en": "🔄 Auto"},
    "creator_arabic": {"ar": "🇸🇦 العربية", "en": "🇸🇦 Arabic"},
    "creator_english": {"ar": "🇺🇸 الإنجليزية", "en": "🇺🇸 English"},
    "creator_chars": {"ar": "حرف", "en": "chars"},
    "creator_method_label": {"ar": "طريقة التوليد", "en": "Generation Method"},
    "creator_cloud": {"ar": "☁️ سحابي (sync.so)", "en": "☁️ Cloud (sync.so)"},
    "creator_cloud_only": {"ar": "التوليد عبر السحابة — جودة عالية وسرعة فائقة", "en": "Cloud generation — high quality, fast speed"},
    "creator_btn_generate": {"ar": "🚀 بدء إنشاء الفيديو", "en": "🚀 Generate Video"},
    "creator_generating": {"ar": "جاري الإنشاء...", "en": "Generating..."},

    # Preview
    "preview_label": {"ar": "المعاينة والنتيجة", "en": "Preview & Result"},
    "preview_placeholder": {"ar": "سينتج الفيديو هنا بعد الإنشاء", "en": "Your video will appear here"},
    "preview_placeholder_hint": {"ar": "يمكنك معاينة وتحميل الفيديو النهائي", "en": "Preview and download your final video"},
    "preview_processing": {"ar": "⏳ جاري معالجة الفيديو...", "en": "⏳ Processing video..."},
    "preview_done": {"ar": "✅ تم إنشاء الفيديو بنجاح!", "en": "✅ Video created successfully!"},
    "preview_error": {"ar": "❌ فشل إنشاء الفيديو", "en": "❌ Video creation failed"},
    "preview_download": {"ar": "⬇ تحميل الفيديو", "en": "⬇ Download Video"},
    "preview_reset": {"ar": "🔄 جديد", "en": "🔄 Reset"},

    # Tips
    "tips_title": {"ar": "نصائح للحصول على أفضل نتيجة", "en": "Tips for Best Results"},
    "tips_1": {"ar": "صورة واضحة: استخدم صورة عالية الجودة مع وجه واضح ومضاء جيداً", "en": "Clear photo: Use a high-quality, well-lit face photo"},
    "tips_2": {"ar": "الصوت المناسب: يفضل صوت واضح بدون ضوضاء خلفية", "en": "Good audio: Use clear audio without background noise"},
    "tips_3": {"ar": "مدة قصيرة: أفضل النتائج مع فيديوهات 15-30 ثانية", "en": "Short duration: Best results with 15-30 second videos"},
    "tips_4": {"ar": "الوضع السحابي: يعطي جودة أفضل", "en": "Cloud mode: Provides better quality"},

    # Creator
    "creator_method_label": {"ar": "طريقة التوليد", "en": "Generation Method"},
    "creator_cloud": {"ar": "سحابي (sync.so)", "en": "Cloud (sync.so)"},
    "creator_cloud_only": {"ar": "التوليد عبر السحابة — جودة عالية وسرعة فائقة", "en": "Cloud generation — high quality, fast speed"},

    # Gallery
    "gallery_title": {"ar": "الفيديوهات المنشأة", "en": "Generated Videos"},
    "gallery_subtitle": {"ar": "جميع الفيديوهات التي تم إنشاؤها باستخدام VideoForge Pro", "en": "All videos created with VideoForge Pro"},
    "gallery_empty": {"ar": "📭 لا توجد فيديوهات بعد. ابدأ بإنشاء أول فيديو!", "en": "📭 No videos yet. Create your first one!"},
    "gallery_loading": {"ar": "جاري تحميل الفيديوهات...", "en": "Loading videos..."},
    "gallery_play": {"ar": "▶️ تشغيل", "en": "▶️ Play"},
    "gallery_download": {"ar": "⬇ تحميل", "en": "⬇ Download"},

    # Stats
    "stat_total": {"ar": "إجمالي الفيديوهات", "en": "Total Videos"},
    "stat_today": {"ar": "فيديو اليوم", "en": "Today's Videos"},
    "stat_status": {"ar": "حالة الخادم", "en": "Server Status"},
    "stat_model": {"ar": "النموذج المحلي", "en": "Local Model"},
    "stat_ready": {"ar": "✅ جاهز", "en": "✅ Ready"},
    "stat_not_found": {"ar": "❌ غير موجود", "en": "❌ Not Found"},

    # CTA
    "cta_title_1": {"ar": "جهز", "en": "Create Your"},
    "cta_title_2": {"ar": "فيديو ناطق احترافي الآن", "en": "Professional Talking Video Now"},
    "cta_subtitle": {"ar": "لا تحتاج إلى خبرة تقنية - فقط اختر صورة واكتب نصاً ودع الذكاء الاصطناعي يعمل", "en": "No technical skills needed - just pick a photo, type text, and let AI do the work"},
    "cta_btn": {"ar": "🚀 ابدأ الآن - مجاناً", "en": "🚀 Start Now - Free"},

    # Footer
    "footer_rights": {"ar": "جميع الحقوق محفوظة", "en": "All rights reserved"},
    "footer_contact": {"ar": "للإعلان", "en": "Advertise"},
    "footer_contact_email": {"ar": "للإعلان: +212 7 79 10 11 09 | admin@videoforge-pro.com", "en": "Advertise: +212 7 79 10 11 09 | admin@videoforge-pro.com"},
    "footer_privacy": {"ar": "سياسة الخصوصية", "en": "Privacy Policy"},
    "footer_terms": {"ar": "شروط الاستخدام", "en": "Terms of Service"},

    # Page titles
    "page_privacy_title": {"ar": "سياسة الخصوصية - VideoForge Pro", "en": "Privacy Policy - VideoForge Pro"},
    "page_terms_title": {"ar": "شروط الاستخدام - VideoForge Pro", "en": "Terms of Service - VideoForge Pro"},

    # Privacy Content
    "privacy_intro": {"ar": "نحن في VideoForge Pro نلتزم بحماية خصوصيتك. توضح هذه السياسة كيفية جمع واستخدام وحماية معلوماتك عند استخدام خدمتنا.", "en": "At VideoForge Pro, we are committed to protecting your privacy. This policy explains how we collect, use, and protect your information when you use our service."},
    "privacy_data_collect_title": {"ar": "ما نقوم بجمعه", "en": "What We Collect"},
    "privacy_data_collect": {"ar": "نقوم بجمع الصور والملفات الصوتية التي ترفعها لإنشاء الفيديوات. لا نقوم بتخزين هذه الملفات لأكثر من 24 ساعة بعد المعالجة. قد نجمع بيانات إحصائية مجهولة المصدر مثل عدد الزيارات والصفحات الأكثر مشاهدة لتحسين الخدمة.", "en": "We collect photos and audio files you upload to create videos. We do not store these files for more than 24 hours after processing. We may collect anonymous statistical data such as visit counts and most viewed pages to improve the service."},
    "privacy_cookies_title": {"ar": "ملفات تعريف الارتباط (Cookies)", "en": "Cookies"},
    "privacy_cookies": {"ar": "نستخدم ملفات تعريف الارتباط لتذكر تفضيلات اللغة وتحسين تجربة المستخدم. نستخدم Google AdSense الذي قد يستخدم ملفات تعريف الارتباط لعرض إعلانات مخصصة حسب اهتماماتك.", "en": "We use cookies to remember language preferences and improve user experience. We use Google AdSense which may use cookies to serve personalized ads based on your interests."},
    "privacy_third_party_title": {"ar": "خدمات الطرف الثالث", "en": "Third-Party Services"},
    "privacy_third_party": {"ar": "نستخدم Google Analytics لتحليل حركة المرور و Google AdSense لعرض الإعلانات. قد تقوم هذه الخدمات بجمع بيانات وفقاً لسياسات الخصوصية الخاصة بها.", "en": "We use Google Analytics for traffic analysis and Google AdSense for displaying ads. These services may collect data according to their own privacy policies."},
    "privacy_rights_title": {"ar": "حقوقك", "en": "Your Rights"},
    "privacy_rights": {"ar": "لديك الحق في طلب حذف جميع بياناتك في أي وقت بالتواصل معنا على +212 7 79 10 11 09 (واتساب) أو contact@videoforge-pro.com.", "en": "You have the right to request deletion of all your data at any time by contacting us at +212 7 79 10 11 09 (WhatsApp) or contact@videoforge-pro.com."},
    "privacy_contact_title": {"ar": "اتصل بنا", "en": "Contact Us"},
    "privacy_contact": {"ar": "للاستفسار عن سياسة الخصوصية: واتساب +212 7 79 10 11 09 | contact@videoforge-pro.com", "en": "For privacy inquiries: WhatsApp +212 7 79 10 11 09 | contact@videoforge-pro.com"},
    "privacy_back": {"ar": "← العودة للرئيسية", "en": "← Back to Home"},

    # Terms Content
    "terms_intro": {"ar": "باستخدامك لموقع VideoForge Pro، فإنك توافق على هذه الشروط. يرجى قراءتها بعناية.", "en": "By using VideoForge Pro, you agree to these terms. Please read them carefully."},
    "terms_service_title": {"ar": "وصف الخدمة", "en": "Service Description"},
    "terms_service": {"ar": "VideoForge Pro هي خدمة ويب مجانية تستخدم تقنية Wav2Lip لتحويل الصور الثابتة إلى فيديوهات ناطقة باستخدام النص أو الصوت.", "en": "VideoForge Pro is a free web service that uses Wav2Lip technology to convert static photos into talking videos using text or audio."},
    "terms_usage_title": {"ar": "الاستخدام المسموح", "en": "Permitted Use"},
    "terms_usage": {"ar": "يُسمح باستخدام الخدمة للأغراض الشخصية والتجارية المشروعة. يُمنع استخدام الخدمة لإنشاء محتوى ضار أو مضلل أو انتهاكي أو مخالف للقوانين.", "en": "The service may be used for legitimate personal and commercial purposes. You may not use the service to create harmful, misleading, abusive, or illegal content."},
    "terms_content_title": {"ar": "مسؤولية المحتوى", "en": "Content Responsibility"},
    "terms_content": {"ar": "أنت وحدك المسؤول عن الصور والملفات الصوتية التي ترفعها والمحتوى الذي تنشئه. نحن لا نحتفظ بحقوق ملكية الفيديوات التي تنشئها.", "en": "You are solely responsible for the photos, audio files you upload, and the content you create. We do not claim ownership of the videos you create."},
    "terms_ads_title": {"ar": "الإعلانات", "en": "Advertisements"},
    "terms_ads": {"ar": "نعرض إعلانات Google AdSense على الموقع. قد تستخدم هذه الإعلانات ملفات تعريف الارتباط لتخصيص الإعلانات حسب اهتماماتك.", "en": "We display Google AdSense ads on the website. These ads may use cookies to personalize ads based on your interests."},
    "terms_changes_title": {"ar": "تغيير الشروط", "en": "Changes to Terms"},
    "terms_changes": {"ar": "نحتفظ بالحق في تعديل هذه الشروط في أي وقت. سيتم إشعار المستخدمين عبر الموقع.", "en": "We reserve the right to modify these terms at any time. Users will be notified via the website."},
    "terms_back": {"ar": "← العودة للرئيسية", "en": "← Back to Home"},

    # Ad Placeholders
    "ad_top": {"ar": "📢 مساحة إعلانية - للإعلان هنا تواصل معنا", "en": "📢 Ad Space - Contact us to advertise here"},
    "ad_in_article": {"ar": "📢 إعلان - دعم الموقع عبر الإعلانات يساعدنا على استمرار الخدمة مجاناً", "en": "📢 Ad - Your support through ads helps us keep the service free"},
    "ad_sidebar": {"ar": "📢 إعلان", "en": "📢 Advertisement"},

    # Language Switcher
    "lang_switch": {"ar": "English", "en": "العربية"},
    "lang_ar": {"ar": "العربية", "en": "Arabic"},
    "lang_en": {"ar": "الإنجليزية", "en": "English"},

    # Errors
    "error_upload": {"ar": "خطأ في رفع الملف", "en": "Upload error"},
    "error_connection": {"ar": "خطأ في الاتصال بالخادم", "en": "Connection error"},
    "error_no_image": {"ar": "يرجى رفع صورة للوجه", "en": "Please upload a face photo"},
    "error_no_audio": {"ar": "يرجى رفع ملف صوتي أو كتابة نص", "en": "Please upload audio or type text"},
    "error_no_model": {"ar": "النموذج المحلي غير موجود. استخدم وضع API السحابي", "en": "Local model not found. Use cloud API mode"},
    "error_no_api_key": {"ar": "يرجى إدخال API Key من sync.so للتوليد السحابي", "en": "Please enter sync.so API Key for cloud generation"},
    "error_tts": {"ar": "فشل توليد الصوت", "en": "TTS generation failed"},
    "toast_success": {"ar": "✅ تم إنشاء الفيديو!", "en": "✅ Video created!"},
    "toast_error": {"ar": "خطأ", "en": "Error"},

    # Upload
    "upload_image_zone": {"ar": "اختر صورة للوجه", "en": "Choose a face photo"},
    "upload_audio_zone": {"ar": "اختر ملف صوتي", "en": "Choose audio file"},
    "upload_image_hint": {"ar": "PNG, JPG, WebP - يفضل صورة واضحة للوجه", "en": "PNG, JPG, WebP - clear face photo preferred"},
    "upload_audio_hint": {"ar": "MP3, WAV, M4A", "en": "MP3, WAV, M4A"},

    # Cloud settings
    "cloud_model": {"ar": "📦 الموديل", "en": "📦 Model"},
    "cloud_model_desc": {"ar": "اختر الموديل المناسب", "en": "Choose the appropriate model"},

    # Model selector
    "model_label": {"ar": "اختيار النموذج", "en": "AI Model"},
}

def get_language():
    """Detect language from session, cookie, or Accept-Language header."""
    if 'lang' in session:
        return session['lang']
    lang = request.cookies.get('lang', '')
    if lang in ('ar', 'en'):
        return lang
    accept = request.headers.get('Accept-Language', '')
    if accept.startswith('en'):
        return 'en'
    return 'ar'

def t(key, lang=None):
    """Get translation for a key in the given language."""
    if lang is None:
        lang = get_language()
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get('ar', key))

def setup_i18n(app_instance):
    """Setup i18n context processor for Flask app."""
    @app_instance.context_processor
    def inject_i18n():
        lang = get_language()
        return {
            'lang': lang,
            't': lambda key: t(key, lang),
            'dir': 'rtl' if lang == 'ar' else 'ltr',
        }

    @app_instance.before_request
    def set_language():
        lang = request.args.get('lang')
        if lang in ('ar', 'en'):
            session['lang'] = lang

    @app_instance.route("/switch-language/<lang>")
    def switch_language(lang):
        if lang in ('ar', 'en'):
            session['lang'] = lang
        referer = request.headers.get('Referer')
        if referer:
            return redirect(referer)
        return redirect('/')
