@echo off
:: ══════════════════════════════════════════════
::  منع الحاسوب من النوم/التعليق
::  شغّله مرة واحدة كـ Administrator
:: ══════════════════════════════════════════════

title منع وضع السكون
color 0E

echo.
echo جاري تعطيل وضع السكون والتعليق...
echo.

:: تعطيل السكون عند التوصيل بالكهرباء
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0

:: تعطيل السكون حتى على البطارية (اختياري - علق السطرين إذا لا تريد)
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-dc 0

:: تعطيل Hibernate تماماً
powercfg /hibernate off

echo.
echo ✅ تم! الحاسوب لن يدخل في وضع السكون بعد الآن
echo ملاحظة: الشاشة قد تُطفأ لكن الحاسوب يبقى يعمل (هذا طبيعي)
echo.
pause
