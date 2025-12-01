start-pick-language = Select language / Tilni tanlang / Выберите язык:
start-welcome = Welcome! Tap “{$menu-find}” to find a car.
menu-title = Main menu:
menu-find = 🔎 Find a car
menu-bookings = 📄 My bookings
menu-help = ℹ️ Help
menu-language = 🌐 Language / Til / Язык
label-class = Class: { $value }
label-drive = Drive: { $value }
session-expired = The session has expired. Please click "Find a car" again and select dates.

# статус в списке "Мои брони"
status-pending = Pending
status-confirmed = Confirmed
status-issued = Issued
status-paid = Paid
status-canceled = Canceled
status-rejected = Rejected
status-expired = Expired

search-context-actions = You can change the class or search dates:
menu-change-class = 🚗 Change car class
menu-change-dates = 📅 Change dates
menu-pay = 💳 Pay
pay-select-type = Select a payment method
pay-full = Full payment
pay-advance = Advance
pay-select-provider = Select a payment system
pay-link = Follow the link to pay: { $url }
back = ◀️ Back

client-booking-confirmed =
    ✅ Your booking has been confirmed!
    🚗 Car: { $title } • Color: { $car_color } • Plate number: { $car_plate_number }
    🆔 Booking ID: #{ $id }
    📅 Period: { $date_from } – { $date_to }
    ℹ️ The partner may contact you to clarify details. Please keep your phone available.

client-booking-paid =
    💳 Payment completed successfully!
    🚗 Car: { $title } • Color: { $car_color } • Plate number: { $car_plate_number }
    🆔 Booking ID: #{ $id }
    📅 Period: { $date_from } – { $date_to }
    👤 Partner: { $partner_name }
    ☎️ Phone: { $partner_phone }
    📍  Address: { $partner_address }
    ✅ Your booking is fully confirmed. Have a great trip!

client-booking-rejected =
    ❌ Unfortunately, your booking request was rejected.
    🚗 Car: { $title } • Color: { $car_color } • Plate number: { $car_plate_number }
    🆔 Booking ID: #{ $id }
    📅 Period: { $date_from } – { $date_to }
    ℹ️ The car is not available for these dates. We’ve selected some similar options for you below.

client-booking-expired =
    ⏳ Booking hold time has expired.
    🚗 Car: { $title } • Color: { $car_color } • Plate number: { $car_plate_number }
    🆔 Booking ID: #{ $id }
    📅 Period: { $date_from } – { $date_to }
    ℹ️ The request was automatically cancelled because it wasn’t confirmed in time. We’ll show you similar cars for these dates.

client-booking-suggest-item =
    • { $title } — { $price_weekday } UZS/day (weekdays), { $price_weekend } UZS/day (weekends)

client-booking-suggest-list =
    🔁 Similar cars you may like:
    { $cars }
    ℹ️ If none of these options works, try changing your dates or car class.

client-booking-suggest-empty =
    😔 We couldn’t find suitable available cars for the selected dates.
    ℹ️ Please try adjusting the dates or choosing a different car class.


# заголовок "мои брони"
my-head = List of your bookings:
my-no-items = You have no active bookings. Click "{ $menu_find }" to search for a car.
my-line = #{ $id } • { $title } • { $status }\n{ $from_ } → { $to }

my-error = Error: { $error }

# показ после отправки брони партнёру
book-sent =
    A request for car rental "{ $title }"
    from { $start } to { $end } has been sent.
    Status: Pending.
    You will receive a notification upon approval or rejection.

book-create-error = Failed to create request. Please try again later.\n{ $error }

# превью перед подтверждением клиентом
book-preview-head = You have selected "{ $title }", { $start }–{ $end }.
book-preview-sum  = Approximately: ≈ { $sum } UZS for { $days } days.
book-preview-ask  = Send a request to a partner?
book-btn-confirm = ✅ Send
book-btn-cancel  = ❌ Cancel

book-cancelled = Canceled.

errors-missing-dates = Not enough information to make a reservation. Please search again.

# choose pay type (оставляем как было)
pay-choose = Select payment type:\n
pay-gw-picked = You have chosen to pay via { $gw } ({ $mode }).\nYour bid number: #{ $bid }.
pay-instruction = Click the button to go to the payment page.
pay-go = 💳 Pay
pay-no-link = Unable to retrieve payment link.
pay-back = Back

lang-set-ok =
    { $done ->
        [uz] Language set to Oʻzbekcha. Now tap “{menu-find}”.
        [en] Language set to English. Now tap “{menu-find}”.
       *[ru] Language set to Russian. Now tap “{menu-find}”.
    }

phone-send = 📱 Send phone number
phone-again = Send your phone using the button below or type it as +998XXXXXXXXX.
reg-ask-first = Enter your first name:
reg-first-short = First name is too short. Please try again.
reg-ask-last = Enter your last name:
reg-last-short = Last name is too short. Please try again.
reg-ok = Registration completed ✅
reg-fail = Registration failed: { $error }

reg-ask-birth = Please enter your date of birth.\nFormat: 01.12.2025
reg-birth-invalid = Invalid date format. Please enter the date in DD.MM.YYYY format. For example, 12/01/2025.
reg-birth-too-young = Requests are accepted only from clients over 18 years of age.
reg-ask-drive-exp = Please indicate your driving experience (in years, numbers only).
reg-drive-exp-invalid = Please enter your length of service using numbers only, without letters or other symbols.

legal-offer = 📄 Public offer
legal-privacy = 🔒 Privacy policy
legal-agree = ✅ I agree
legal-decline = ✖️ Cancel
legal-prompt = To continue, you must accept the Public Offer and the Privacy Policy. Review them and press “✅ I agree”.
legal-send-offer-fail = Could not send the offer file.
legal-offer-missing = Offer file not found.
legal-send-privacy-fail = Could not send the policy file.
legal-privacy-missing = Policy file not found.
legal-declined = You declined the terms. Registration cannot proceed without consent.

cal-today = Today
cal-tomorrow = Tomorrow
cal-weekdays = Mo,Tu,We,Th,Fr,Sa,Su

search-date-from = 📅 Select the rental start date:
search-date-to = 📅 Start date: { $start }\nNow select the rental end date:
search-warn-past = You cannot select a past date
search-warn-end-gt-start = End date must be later than the start date
search-period = 🗓 Period: { $start } → { $end }\n\nChoose a car class:
search-results-none = No suitable cars found. Try another class or change the dates.
search-results-head = Found { $count } cars.{ $extra }
showing-first-10 = Showing the first 10.
search-classes-head = Choose another class or change the dates:

class-eco = Economy
class-comfort = Comfort
class-business = Business
class-premium = Premium
class-suv = SUV
class-minivan = Minivan
back-to-dates = « Back to dates

card-top = Region: { $region }\nPlate number: { $plate_number }\n🚗 { $title }{ $year_part }{ $mileage_part } • Color: { $color }
card-line2 = ⚙️ { $class_part }{ $drive_part }{ $gearbox_part }
engine_volume_text = engine displacement: { $engine_volume_l }
card-price = 🗓 Weekdays: { $wd } UZS/day\n📅 Weekends: { $we } UZS/day
card-terms = 💳 Deposit: { $deposit }\n💳 Advance: { $advance }\n✒️ Mileage limit: { $limit } km/day\n🛡️ Insurance: { $ins }
card-options-title = 🎁 Options:
card-option-child = • 👶 Child seat (+per tariff)
card-option-delivery = • 📍 Delivery/pick-up at address
card-option-driver = • 🚘 Car with driver
card-fallback = { $caption }
card-age = Client age: from { $age } years
card-drive-exp = Driving experience: from { $years } years
card-passport-required = Required: passport or ID card
label-gear = Transmission: { $value }

drive-fwd = FWD
drive-rwd = RWD
drive-awd = AWD

gearbox_at = Automatic
gearbox_mt = Manual
gearbox_amt = Robotized
gearbox_cvt = CVT

fuel-petrol = Petrol
fuel-diesel = Diesel
fuel-gas = Gas
fuel-hybrid = Hybrid
fuel-electric = Electric

deposit-none = No deposit
advance-none = No advance
deposit-low = Low deposit
deposit-high = High deposit

ins-included = included
ins-excluded = not included

btn-more = 📷 Interior photos
btn-terms = 📋 Terms
btn-reviews = 💬 Reviews
btn-book = ✅ Book

terms-title = 📋 Rental terms for “{ $title }”:
terms-deposit = • 💳 Deposit: { $deposit }
terms-advance = • 💳 Advance: { $advance }
terms-limit = • ✒️ Mileage limit: { $limit } km/day (above this — partner’s tariff applies)
terms-ins = • 🛡️ Insurance: { $ins }
terms-driver = • 🚘 Car with driver: { $has ->
    [yes] yes
   *[no]  no
}
terms-delivery = • 📍 Delivery: { $has ->
    [yes] available
   *[no]  no
}
terms-child = • 👶 Child seat: { $has ->
    [yes] available
   *[no]  no
}
terms-age = Minimum client age: { $age } years
terms-drive-exp = Minimum driving experience: { $years } years
terms-passport = Passport/ID card: { $has ->
    [yes] Yes
   *[no]  No
}
terms-no-more-photos = No additional photos.
terms-car-not-found = Car not found

reviews-soon = Reviews section is coming soon.
errors-car-not-found = Car not found

reg-before-booking = Please register to submit car reservation requests.
book-confirm-q = You selected: { $title }\nPeriod: { $start } → { $end }\nEstimated: ~{ $sum } UZS for { $days } days.\n\nConfirm sending the request to the partner?
book-ask-contact = You selected { $title }, { $start }–{ $end }\nPlease share your contact phone:
book-btn-confirm = ✅ Confirm
book-btn-cancel = ✖️ Cancel
book-canceled = Request cancelled.
book-create-fail = Could not create the request: { $error }
book-created = The rental request for “{ $title }” from { $start } to { $end } was sent to the partner. Status: Under review.\nYou will be notified upon confirmation/rejection.
selfie-ask = Please submit a selfie (face photo). Acceptable formats: JPG/PNG.
selfie-invalid = Please send a regular photo (JPG/PNG), not a sticker or video.
selfie-save-fail = Selfie failed to save: {error}

my-no-items = You have no bookings yet. Use “{$menu-find}” to make your first booking.
my-error = Failed to load bookings: { $error }
my-head = Your bookings:
my-line = #{ $id } • { $title } • { $status }\n{ $from_ } → { $to }


status-paid = ✅ Payment for request #{id} ("{$title}") has been received. Thank you!

pay-mode-full = 💳 Full payment ({ $amount } UZS)
pay-mode-adv = 🔖 Advance payment ({ $amount } UZS)

pay-choose-type = 💰 Select payment type:
pay-choose-provider = 💳 Select a payment system:

pay-open-link = 🔗 Click the link below to proceed with the payment:\n\n👉 [💳 Pay]({ $pay_url})
pay-amount-zero = ⚠️ Cannot create payment: amount is zero.

pay-choose-full = Choose a payment provider for full payment:
pay-choose = Select payment type:
pay-choose-adv = Choose a payment provider for the advance payment:
pay-back = Go back to the previous message and choose a payment option.
pay-gw-picked = You chose to pay via { $gw } ({ $mode }).\n\nYour request number: #{ $bid }.
pay-full-btn = 💳 Pay full amount ({ $total } UZS)
pay-adv-btn = 💸 Pay advance ({ $adv } UZS)
pay-go = 💳 Pay
pay-instruction = Tap the button to open the payment page.
pay-no-link = Payment link is not available. Please try later.

suggest-none = No suitable alternatives found. Try changing dates or car class.
suggest-head = You might like these options:
suggest-tail = To continue searching, tap “{$menu-find}”.

notify-confirmed = ✅ Booking #{ $id } for “{ $title }”, { $start }–{ $end } has been confirmed by the partner.
notify-rejected = ❌ Booking #{ $id } for “{ $title }”, { $start }–{ $end } has been rejected by the partner.
notify-expired = ⏳ Booking #{ $id } for “{ $title }”, { $start }–{ $end } has expired/cancelled.
