menu-title = Главное меню:
menu-find = 🔎 Найти авто
menu-bookings = 📄 Мои брони
menu-help = ℹ️ Помощь
menu-language = 🌐 Язык / Language / Til
# === start & language ===
start-pick-language = Выберите язык / Select language / Tilni tanlang:
start-welcome = Добро пожаловать! Нажмите «{menu-find}», чтобы подобрать машину.

lang-set-ok =
    { $done ->
        [uz] Язык установлен: Oʻzbekcha. Теперь нажмите «{menu-find}».
        [en] Language set to English. Now tap “{menu-find}”.
       *[ru] Язык установлен: Русский. Теперь нажмите «{menu-find}».
    }

# === phone & registration ===
phone-send = 📱 Отправить телефон
phone-again = Отправьте телефон кнопкой ниже или введите в формате +998XXXXXXXXX.
reg-ask-first = Введите ваше имя:
reg-first-short = Имя слишком короткое. Повторите, пожалуйста.
reg-ask-last = Введите вашу фамилию:
reg-last-short = Фамилия слишком короткая. Повторите, пожалуйста.
reg-ok = Регистрация завершена ✅
reg-fail = Регистрация не удалась: { $error }

# === legal ===
legal-offer = 📄 Публичная оферта
legal-privacy = 🔒 Политика конфиденциальности
legal-agree = ✅ Согласен
legal-decline = ✖️ Отмена
legal-prompt = Для продолжения необходимо согласиться с Публичной офертой и Политикой конфиденциальности. Ознакомьтесь и нажмите «✅ Согласен».
legal-send-offer-fail = Не удалось отправить файл оферты.
legal-offer-missing = Файл оферты не найден.
legal-send-privacy-fail = Не удалось отправить файл политики.
legal-privacy-missing = Файл политики не найден.
legal-declined = Вы отказались от условий. Без согласия регистрация невозможна.

# === calendar ===
cal-today = Сегодня
cal-tomorrow = Завтра
cal-weekdays = Пн,Вт,Ср,Чт,Пт,Сб,Вс

# === search flow ===
search-date-from = 📅 Выберите дату начала аренды:
search-date-to = 📅 Дата начала: { $start }\nТеперь выберите дату окончания аренды:
search-warn-past = Нельзя выбирать прошлую дату
search-warn-end-gt-start = Окончание должно быть позже начала
search-period = 🗓 Период: { $start } → { $end }\n\nВыберите класс авто:
search-results-none = К сожалению, подходящих авто не найдено. Попробуйте другой класс или измените даты.
search-results-head = Найдено { $count } авто.{ $extra }
showing-first-10 = Показаны первые 10.
    }
search-classes-head = Выберите другой класс или измените даты:

class-eco = Эконом
class-comfort = Комфорт
class-business = Бизнес
class-premium = Премиум
class-suv = Внедорожник
class-minivan = Минивэн
back-to-dates = « Назад к датам

# === car card ===
card-top = 🚗 { $title }{ $year_part }{ $mileage_part }
card-line2 = ⚙️ { $class_label }{ $drive_part }
card-price = 🗓 Будни: { $wd } сум/сутки\n📅 Выходные: { $we } сум/сутки
card-terms = 💳 Депозит: { $deposit }\n✒️ Лимит пробега: { $limit } км/сутки\n🛡️ Страховка: { $ins }
card-options-title = 🎁 Опции:
card-option-child = • 👶 Детское кресло (+по тарифу)
card-option-delivery = • 📍 Доставка/возврат по адресу
card-fallback = { $caption }
label-class = Класс: { $value }
label-drive = Привод: { $value }

drive-fwd = Передний
drive-rwd = Задний
drive-awd = Полный

fuel-petrol = Бензин
fuel-diesel = Дизель
fuel-gas = Газ
fuel-hybrid = Гибрид
fuel-electric = Электро

deposit-none = Без залога
deposit-low = Низкий залог
deposit-high = Высокий залог

ins-included = включена
ins-excluded = не включена

btn-more = 📷 Фото салона
btn-terms = 📋 Условия
btn-reviews = 💬 Отзывы
btn-book = ✅ Забронировать

# === terms dialog & errors ===
terms-title = 📋 Условия аренды для «{ $title }»:
terms-deposit = • 💳 Депозит: { $deposit }
terms-limit = • ✒️ Лимит пробега: { $limit } км/сутки (свыше — по тарифу партнёра)
terms-ins = • 🛡️ Страховка: { $ins }
terms-driver = • 🚘 Авто с водителем: { $has ->
    [yes] да
   *[no]  нет
}
terms-delivery = • 📍 Доставка: { $has ->
    [yes] доступна
   *[no]  нет
}
terms-child = • 👶 Детское кресло: { $has ->
    [yes] есть
   *[no]  нет
}
terms-no-more-photos = Дополнительных фото нет.
terms-car-not-found = Авто не найдено

reviews-soon = Раздел с отзывами скоро будет доступен.
errors-car-not-found = Авто не найдено

# === booking ===
book-confirm-q = Вы выбрали: { $title }\nПериод: { $start } → { $end }\nОриентировочно: ~{ $sum } UZS за { $days } д.\n\nПодтвердить отправку заявки партнёру?
book-ask-contact = Вы выбрали { $title }, { $start }–{ $end }\nОставьте контакты для связи:
book-btn-confirm = ✅ Подтвердить
book-btn-cancel = ✖️ Отмена
book-canceled = Заявка отменена.
book-create-fail = Не удалось создать заявку: { $error }
book-created = Заявка на аренду машины «{ $title }» с { $start } до { $end } отправлена партнёру. Статус: На проверке.\nВы получите уведомление при подтверждении/отклонении.

# === my bookings ===
my-no-items = У вас пока нет броней. Используйте «{$menu-find}», чтобы оформить первую.
my-error = Не удалось загрузить список броней: { $error }
my-head = Ваши брони:
my-line = #{ $id } • { $title } • { $status }\n{ $from_ } → { $to }

# === payments ===
pay-choose-full = Выберите платёжную систему для полной оплаты:
pay-choose-adv = Выберите платёжную систему для оплаты аванса:
pay-choose = Выберите тип оплаты:
pay-back = Вернитесь к предыдущему сообщению и выберите вариант оплаты.
pay-gw-picked = Вы выбрали оплату через { $gw } ({ $mode }).\n\nНомер вашей заявки: #{ $bid }.
pay-mode-full = полная сумма
pay-mode-adv = аванс
pay-full-btn = 💳 Оплатить полную сумму ({ $total } UZS)
pay-adv-btn = 💸 Оплатить аванс ({ $adv } UZS)
pay-go = 💳 Оплатить
pay-instruction = Нажмите кнопку, чтобы перейти на страницу оплаты.
pay-no-link = Ссылка для оплаты недоступна. Попробуйте позже.

# === suggestions ===
suggest-none = Подходящих альтернатив не найдено. Попробуйте изменить даты или класс авто.
suggest-head = Возможно, вам подойдут эти варианты:
suggest-tail = Чтобы продолжить поиск, нажмите «{menu-find}».

# === notifications ===
notify-confirmed = ✅ Бронь #{ $id } по авто «{ $title }» на { $start }–{ $end } подтверждена партнёром.
notify-rejected = ❌ Бронь #{ $id } по авто «{ $title }» на { $start }–{ $end } отклонена партнёром.
notify-expired = ⏳ Бронь #{ $id } по авто «{ $title }» на { $start }–{ $end } истекла/отменена.
