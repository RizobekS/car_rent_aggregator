start-pick-language = Select language / Tilni tanlang / Выберите язык:
start-welcome = Welcome! Tap “{$menu-find}” to find a car.
menu-title = Main menu:
menu-find = 🔎 Find a car
menu-bookings = 📄 My bookings
menu-help = ℹ️ Help
menu-language = 🌐 Language / Til / Язык
label-class = Class: { $value }
label-drive = Drive: { $value }

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

card-top = 🚗 { $title }{ $year_part }{ $mileage_part }
card-line2 = ⚙️ { $class_label }{ $drive_part }
card-price = 🗓 Weekdays: { $wd } UZS/day\n📅 Weekends: { $we } UZS/day
card-terms = 💳 Deposit: { $deposit }\n✒️ Mileage limit: { $limit } km/day\n🛡️ Insurance: { $ins }
card-options-title = 🎁 Options:
card-option-child = • 👶 Child seat (+per tariff)
card-option-delivery = • 📍 Delivery/pick-up at address
card-fallback = { $caption }

drive-fwd = FWD
drive-rwd = RWD
drive-awd = AWD

fuel-petrol = Petrol
fuel-diesel = Diesel
fuel-gas = Gas
fuel-hybrid = Hybrid
fuel-electric = Electric

deposit-none = No deposit
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
terms-no-more-photos = No additional photos.
terms-car-not-found = Car not found

reviews-soon = Reviews section is coming soon.
errors-car-not-found = Car not found

book-confirm-q = You selected: { $title }\nPeriod: { $start } → { $end }\nEstimated: ~{ $sum } UZS for { $days } days.\n\nConfirm sending the request to the partner?
book-ask-contact = You selected { $title }, { $start }–{ $end }\nPlease share your contact phone:
book-btn-confirm = ✅ Confirm
book-btn-cancel = ✖️ Cancel
book-canceled = Request cancelled.
book-create-fail = Could not create the request: { $error }
book-created = The rental request for “{ $title }” from { $start } to { $end } was sent to the partner. Status: Under review.\nYou will be notified upon confirmation/rejection.

my-no-items = You have no bookings yet. Use “{$menu-find}” to make your first booking.
my-error = Failed to load bookings: { $error }
my-head = Your bookings:
my-line = #{ $id } • { $title } • { $status }\n{ $from_ } → { $to }

pay-choose-full = Choose a payment provider for full payment:
pay-choose = Select payment type:
pay-choose-adv = Choose a payment provider for the advance payment:
pay-back = Go back to the previous message and choose a payment option.
pay-gw-picked = You chose to pay via { $gw } ({ $mode }).\n\nYour request number: #{ $bid }.
pay-mode-full = full amount
pay-mode-adv = advance
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
