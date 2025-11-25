start-pick-language = Tilni tanlang / Select language / Выберите язык:
start-welcome = Xush kelibsiz! Mashinani tanlash uchun «{$menu-find}» tugmasini bosing.
menu-title = Asosiy menyu:
menu-find = 🔎 Mashina topish
menu-bookings = 📄 Mening bronlarim
menu-help = ℹ️ Yordam
menu-language = 🌐 Til / Language / Язык
session-expired = Sessiya muddati tugadi. Iltimos, qaytadan "Avtomobil topish" tugmasini bosing va sanalarni tanlang.

# статус в списке "Мои брони"
status-pending = Tekshiruvda
status-confirmed = Tasdiqlangan
status-issued = Rasmiylashtirilgan
status-paid = To‘langan
status-canceled = Bekor qilindi
status-rejected = Rad etilgan
status-expired = Muddati tugagan

# заголовок "мои брони"
my-head = Arizalar to‘plami:
my-no-items = Hozirda sizda ariza mavjud emas. Avtomobil topish uchun, «{ $menu_find }», tugmasini bosing.
my-line = #{ $id } • { $title } • { $status }\n{ $from_ } → { $to }

my-error = Hatolik: { $error }

# показ после отправки брони партнёру
book-sent =
    { $start } dan { $end } gacha "{ $title }" Avtomobilini ijaraga olish uchun ariza yuborildi.
    Status: Tekshiruvda.
    Arizangiz bo'yicha qabul qilinganlik yoki rad qilinganligi to‘g‘risida habar beramiz.

book-create-error = Ariza yaratish imkoni bo‘lmadi. Keynroq urunib ko‘ring.\n{ $error }

# превью перед подтверждением клиентом
book-preview-head = Siz «{ $title }» avtomobilini tanladingiz, { $start }–{ $end }.
book-preview-sum  = Hisoblangan narx: ≈ { $sum } UZS { $days } kun uchun.
book-preview-ask  = Tasdiqlaysizmi?
book-btn-confirm = ✅ Tastiqlash
book-btn-cancel  = ❌ Bekor qilish

book-cancelled = Ariza bekor qilindi.

errors-missing-dates = Ariza qoldirish uchun ma‘lumotlar etarli emas. Qidiruvni takrorlang.

# choose pay type (оставляем как было)
pay-choose = To‘lov turini tanlang:\n
pay-mode-full = To'liq narx
pay-mode-adv  = Oldindan to‘lov
pay-choose-full = To‘lov turini tanlang (to‘liq narx):
pay-choose-adv  = To‘lov turini tanlang (oldindan to‘lov):
pay-gw-picked = Siz to‘lov turi uchun { $gw } ({ $mode }) ni tanladingiz.\nSizning ariza raqamingiz: #{ $bid }.
pay-instruction = To‘lov sahifasiga o‘tish uchun, To‘lash tugmasini bosing.
pay-go = 💳 To‘lash
pay-no-link = To‘lash uchun havola topilmadi.
pay-back = Ortga

label-class = Klass: { $value }
label-drive = Privod: { $value }

lang-set-ok =
    { $done ->
        [uz] Til o‘rnatildi. Endi «{menu-find}» tugmasini bosing.
        [en] Til English qilib o‘rnatildi. Endi “{menu-find}” tugmasini bosing.
       *[ru] Til Русский qilib o‘rnatildi. Endi «{menu-find}» tugmasini bosing.
    }

phone-send = 📱 Telefonni yuborish
phone-again = Pastdagi tugma orqali telefon raqamingizni yuboring yoki +998XXXXXXXXX formatida kiriting.
reg-ask-first = Ismingizni kiriting:
reg-first-short = Ism juda qisqa. Iltimos, qaytadan kiriting.
reg-ask-last = Familiyangizni kiriting:
reg-last-short = Familiya juda qisqa. Iltimos, qaytadan kiriting.
reg-ok = Ro‘yxatdan o‘tish yakunlandi ✅
reg-fail = Ro‘yxatdan o‘tish amalga oshmadi: { $error }

legal-offer = 📄 Ommaviy oferta
legal-privacy = 🔒 Maxfiylik siyosati
legal-agree = ✅ Roziman
legal-decline = ✖️ Bekor qilish
legal-prompt = Davom etish uchun Ommaviy oferta va Maxfiylik siyosatiga rozilik bildirishingiz lozim. Tanishib chiqing va «✅ Roziman» ni bosing.
legal-send-offer-fail = Oferta faylini yuborib bo‘lmadi.
legal-offer-missing = Oferta fayli topilmadi.
legal-send-privacy-fail = Siyosat faylini yuborib bo‘lmadi.
legal-privacy-missing = Siyosat fayli topilmadi.
legal-declined = Siz shartlarga rozi bo‘lmadingiz. Roziliksiz ro‘yxatdan o‘tib bo‘lmaydi.

cal-today = Bugun
cal-tomorrow = Ertaga
cal-weekdays = Du,Se,Ch,Pa,Ju,Sh,Ya

search-date-from = 📅 Ijara boshlanish sanasini tanlang:
search-date-to = 📅 Boshlanish sanasi: { $start }\nEndi ijaraning tugash sanasini tanlang:
search-warn-past = O‘tgan sanani tanlab bo‘lmaydi
search-warn-end-gt-start = Tugash sana boshlanish sanasidan keyin bo‘lishi kerak
search-period = 🗓 Davr: { $start } → { $end }\n\nAvto klassini tanlang:
search-results-none = Afsus, mos avtomobillar topilmadi. Boshqa klassni tanlang yoki sanalarni o‘zgartiring.
search-results-head = Topildi: { $count } ta avto.{ $extra }
search-classes-head = Boshqa klassni tanlang yoki sanalarni o‘zgartiring:
showing-first-10 = Dastlabki 10 tasi ko‘rsatildi.

class-eco = Ekonom
class-comfort = Komfort
class-business = Biznes
class-premium = Premium
class-suv = Yo‘l tanlamas
class-minivan = Miniven
back-to-dates = « Sanalarga qaytish

card-top =
    🚗 { $title }{ $year ->
        [has]  ({ $y })
       *[no]
    }{ $mileage ->
        [has]  • Yurgani: { $km } km
       *[no]
    }
card-line2 =
    ⚙️ Klass: { $_class }{ $drive ->
        [has]  • Privod: { $drive_2 }
       *[no]
    }
card-price = 🗓 Ish kunlari: { $wd } so‘m/sutka\n📅 Dam olish kunlari: { $we } so‘m/sutka
card-terms = 💳 Garov: { $deposit }\n💳 Oldindan to'lov: { $advance }\n✒️ Kunlik limit: { $limit } km/sutka\n🛡️ Sug‘urta: { $ins }
card-options-title = 🎁 Opsiyalar:
card-option-child = • 👶 Bolalar o‘rindig‘i (+tarif bo‘yicha)
card-option-delivery = • 📍 Manzil bo‘yicha yetkazib berish/qabul qilish
card-option-driver = • 🚘 Avtomobil haydovchisi bilan
card-fallback = { $caption }
card-age = Mijoz yoshi: { $age } yoshdan boshlab
card-drive-exp = Haydash tajribasi: {$years} yildan boshlab
card-passport-required = Talab qilinadi: pasport yoki shaxsni tasdiqlovchi hujjat

drive-fwd = Oldingi
drive-rwd = Orqa
drive-awd = To‘liq

fuel-petrol = Benzin
fuel-diesel = Dizel
fuel-gas = Gaz
fuel-hybrid = Gibrid
fuel-electric = Elektr

deposit-none = Garovsiz
advance-none = Oldindan to'lovsiz
deposit-low = Past garov
deposit-high = Yuqori garov

ins-included = kiritilgan
ins-excluded = kiritilmagan

btn-more = 📷 Salon fotosi
btn-terms = 📋 Shartlar
btn-reviews = 💬 Fikrlar
btn-book = ✅ Bron qilish

terms-title = 📋 «{ $title }» uchun ijaraning shartlari:
terms-deposit = • 💳 Garov: { $deposit }
terms-advance = • 💳 Oldindan to'lov: { $advance }
terms-limit = • ✒️ Kunlik limit: { $limit } km/sutka (ortig‘i — hamkor tarifiga binoan)
terms-ins = • 🛡️ Sug‘urta: { $ins }
terms-driver = • 🚘 Haydovchi bilan: { $has ->
    [yes] ha
   *[no]  yo‘q
}
terms-delivery = • 📍 Yetkazib berish: { $has ->
    [yes] mavjud
   *[no]  yo‘q
}
terms-child = • 👶 Bolalar o‘rindig‘i: { $has ->
    [yes] bor
   *[no]  yo‘q
}
terms-age = Mijozning minimal talab qilinadigan yoshi: { $age } yosh
terms-drive-exp = Minimal talab qilinadigan haydash tajribasi: { $years } yil
terms-passport = Pasport/shaxsni tasdiqlovchi hujjat: { $has ->
    [yes] bor
   *[no]  yo'q
}
terms-no-more-photos = Qo‘shimcha foto mavjud emas.
terms-car-not-found = Avtomobil topilmadi

reviews-soon = Fikr-mulohazalar bo‘limi tez orada ishga tushadi.
errors-car-not-found = Avtomobil topilmadi

book-confirm-q = Siz tanladingiz: { $title }\nDavr: { $start } → { $end }\nTaxminan: ~{ $sum } UZS ({ $days } kun).\n\nSo‘rovni hamkorga yuborishni tasdiqlaysizmi?
book-ask-contact = Siz { $title } tanladingiz, { $start }–{ $end }\nAloqa uchun telefoningizni yuboring:
book-btn-confirm = ✅ Tasdiqlash
book-btn-cancel = ✖️ Bekor qilish
book-canceled = So‘rov bekor qilindi.
book-create-fail = So‘rovni yaratib bo‘lmadi: { $error }
book-created = «{ $title }» mashinasini { $start } dan { $end } gacha ijaraga olish bo‘yicha so‘rov hamkorga yuborildi. Holat: Tekshiruvda.\nTasdiqlanganda/ rad etilganda xabarnoma olasiz.
selfie-ask = Iltimos, selfi (yuz fotosurati) yuboring. Qabul qilinadigan formatlar: JPG/PNG.
selfie-invalid = Iltimos, stiker yoki video emas, oddiy rasm (JPG/PNG) yuboring.
selfie-save-fail = Selfi saqlanmadi: {error}

my-no-items = Sizda hozircha bronlar yo‘q. Birinchi bronni rasmiylashtirish uchun «{$menu-find}» tugmasini bosing.
my-error = Bronlar ro‘yxatini yuklab bo‘lmadi: { $error }
my-head = Bronlaringiz:
my-line = #{ $id } • { $title } • { $status }\n{ $from_ } → { $to }

status-paid = ✅ #{id} ("{$title}") so'rovi uchun to'lov qabul qilindi. Rahmat!

pay-choose-full = To‘liq to‘lov uchun to‘lov tizimini tanlang:
pay-choose-adv = Oldindan to‘lov uchun to‘lov tizimini tanlang:
pay-choose = To'lov turini tanlang:
pay-back = Oldingi xabarga qaytib, to‘lov variantini tanlang.
pay-gw-picked = Siz { $gw } orqali ({ $mode }) to‘lovni tanladingiz.\n\nSo‘rov raqami: #{ $bid }.
pay-mode-full = to‘liq summa
pay-mode-adv = avans
pay-full-btn = 💳 To‘liq to‘lash ({ $total } UZS)
pay-adv-btn = 💸 Avans to‘lash ({ $adv } UZS)
pay-go = 💳 To‘lash
pay-instruction = To‘lov sahifasiga o‘tish uchun tugmani bosing.
pay-no-link = To‘lov havolasi hozircha mavjud emas.

suggest-none = Mos alternativalar topilmadi. Sanalarni yoki klassni o‘zgartirib ko‘ring.
suggest-head = Ehtimol, quyidagi variantlar mos kelar:
suggest-tail = Qidirishni davom ettirish uchun «{$menu-find}» tugmasini bosing.

notify-confirmed = ✅ #{ $id } bron — «{ $title }», { $start }–{ $end } — hamkor tomonidan tasdiqlandi.
notify-rejected = ❌ #{ $id } bron — «{ $title }», { $start }–{ $end } — hamkor tomonidan rad etildi.
notify-expired = ⏳ #{ $id } bron — «{ $title }», { $start }–{ $end } — muddati tugadi/bekor qilindi.
