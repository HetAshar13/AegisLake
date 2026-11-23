select *
from (values
    ('card_eur', 'EUR', 10000),
    ('card_jpy', 'JPY', 10000)
) as payments(case_id, currency, amount_minor)
