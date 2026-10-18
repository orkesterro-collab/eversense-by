<?php
/**
 * Настройки стран. Страна выбирается константой EVERSENSE_COUNTRY в wp-config.php
 * (по умолчанию «by»). Значения contacts — стартовые: дальше всё редактируется
 * в админке, «Внешний вид → Настройки EVERSENSE».
 *
 * languages: первый язык — основной (без префикса в адресе).
 */
return [
	'by' => [
		'name'      => 'Беларусь',
		'timezone'  => 'Europe/Minsk',
		'languages' => [
			[ 'slug' => 'ru', 'locale' => 'ru_RU', 'name' => 'Русский',    'short' => 'Ru', 'flag' => 'by' ],
			[ 'slug' => 'be', 'locale' => 'bel', 'name' => 'Беларуская', 'short' => 'Be', 'flag' => 'by' ],
		],
		'map_center' => [ 53.9006, 27.5590 ], // Минск
		'map_zoom'   => 7,
		'defaults'   => [
			'phone'          => '',
			'phone_2'        => '',
			'email'          => '',
			'company_ru'     => 'ООО «Флорсток»',
			'company_be'     => 'ТАА «Флорсток»',
			'requisites_ru'  => '',
			'requisites_be'  => '',
			'office_ru'      => '',
			'office_be'      => '',
			'warehouse_ru'   => '',
			'warehouse_be'   => '',
			'hours_ru'       => 'Пн–Пт: 9:00–18:00',
			'hours_be'       => 'Пн–Пт: 9:00–18:00',
		],
	],
	'kz' => [
		'name'      => 'Казахстан',
		'timezone'  => 'Asia/Almaty',
		'languages' => [
			[ 'slug' => 'ru', 'locale' => 'ru_RU', 'name' => 'Русский', 'short' => 'Ru', 'flag' => 'kz' ],
			[ 'slug' => 'kk', 'locale' => 'kk',    'name' => 'Қазақша', 'short' => 'Kk', 'flag' => 'kz' ],
		],
		'map_center' => [ 43.2389, 76.8897 ], // Алматы
		'map_zoom'   => 5,
		'defaults'   => [
			'phone'          => '+7 (700) 000-00-00',
			'phone_2'        => '',
			'email'          => 'info@eversense.kz',
			'company_ru'     => 'ТОО «Название дистрибьютора»',
			'company_kk'     => '«Дистрибьютор атауы» ЖШС',
			'requisites_ru'  => 'БИН 000000000000',
			'requisites_kk'  => 'БСН 000000000000',
			'office_ru'      => 'Алматы, ул. Примерная, 1',
			'office_kk'      => 'Алматы, Мысал к-сі, 1',
			'warehouse_ru'   => '',
			'warehouse_kk'   => '',
			'hours_ru'       => 'Пн–Пт: 9:00–18:00',
			'hours_kk'       => 'Дс–Жм: 9:00–18:00',
		],
	],
];
