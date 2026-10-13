<?php
/**
 * Стартовые данные каталога — по ever-home.ru (октябрь 2026).
 * Используются один раз командой `wp eversense seed`; дальше всё правится в админке.
 * tone — цвет-заглушка, пока не загружено фото декора.
 */

$classic = [ 'format' => 'Classic', 'size' => '1292 × 193 мм', 'pack_area' => '1,99 м²' ];
$large   = [ 'format' => 'Large',   'size' => '1292 × 246 мм', 'pack_area' => '2,54 м²' ];
$common  = [ 'thickness' => '8 мм', 'lock' => 'CLIC it!', 'chamfer' => 'V4', 'pack_pcs' => '8' ];

return [
	'series' => [
		'new-minimalism' => [
			'order' => 1,
			'ru'    => [
				'name' => 'Новый минимализм',
				'lead' => 'Светлые декоры для комнат, полных света, — жилых пространств, фотостудий, интерьеров, решённых в минималистичном духе.',
				'text' => '',
			],
			'be'    => [
				'name' => 'Новы мінімалізм',
				'lead' => 'Светлыя дэкоры для пакояў, поўных святла, — жылых прастор, фотастудый, інтэр’ераў, вырашаных у мінімалістычным духу.',
				'text' => '',
			],
		],
		'quiet-luxury' => [
			'order' => 2,
			'ru'    => [
				'name' => 'Тихая роскошь',
				'lead' => 'Новый чёрный от Eversense: глубокие, насыщенные тона для выразительных интерьеров.',
				'text' => 'Фактура дерева с точным совпадением рисунка и текстуры: сучки и кольца в досках повторяют натуральный рельеф древесных слэбов.',
			],
			'be'    => [
				'name' => 'Ціхая раскоша',
				'lead' => 'Новы чорны ад Eversense: глыбокія, насычаныя тоны для выразных інтэр’ераў.',
				'text' => 'Фактура дрэва з дакладным супадзеннем малюнка і тэкстуры: сукі і кольцы ў дошках паўтараюць натуральны рэльеф драўляных слэбаў.',
			],
		],
		'nature-aesthetic' => [
			'order' => 3,
			'ru'    => [
				'name' => 'Природная эстетика',
				'lead' => 'Матовые натуральные оттенки для интерьеров в стиле slow living.',
				'text' => 'Трендовые декоры с текстурой древесины и бархатистыми поверхностями.',
			],
			'be'    => [
				'name' => 'Прыродная эстэтыка',
				'lead' => 'Матавыя натуральныя адценні для інтэр’ераў у стылі slow living.',
				'text' => 'Модныя дэкоры з тэкстурай драўніны і аксамітнымі паверхнямі.',
			],
		],
	],

	// [ slug, серия, ru-название, ru-отделка, be-название, be-отделка, артикул, формат, tone ]
	'decors' => array_map(
		static function ( $d ) use ( $classic, $large, $common ) {
			[ $slug, $series, $ru, $ru_f, $be, $be_f, $code, $fmt, $tone ] = $d;
			return [
				'slug'   => $slug,
				'series' => $series,
				'code'   => $code,
				'tone'   => $tone,
				'ru'     => [ 'name' => $ru, 'finish' => $ru_f ],
				'be'     => [ 'name' => $be, 'finish' => $be_f ],
				'specs'  => array_merge( $common, 'large' === $fmt ? $large : $classic ),
			];
		},
		[
			// Новый минимализм
			[ 'jura',                    'new-minimalism',   'Однотонный',    'Бежевый песок',      'Аднатонны',       'Бэжавы пясок',       'EL153',  'classic', '#d9c7ad' ],
			[ 'taupe-grey',              'new-minimalism',   'Однотонный',    'Ярко-серый',         'Аднатонны',       'Ярка-шэры',          'EL750',  'classic', '#b7b4ae' ],
			[ 'victoria-oak-white',      'new-minimalism',   'Дуб Виктория',  'Белый',              'Дуб Вікторыя',    'Белы',               'EL1049', 'classic', '#e8e1d6' ],
			[ 'light-gray-victoria-oak', 'new-minimalism',   'Дуб Виктория',  'Светло-серый',       'Дуб Вікторыя',    'Светла-шэры',        'EL1050', 'classic', '#cfc9bf' ],
			[ 'grey-victoria-oak',       'new-minimalism',   'Дуб Виктория',  'Серый',              'Дуб Вікторыя',    'Шэры',               'EL1053', 'classic', '#a9a296' ],
			[ 'grey-lavaredo-oak',       'new-minimalism',   'Дуб Лаваредо',  'Серый',              'Дуб Лаварэда',     'Шэры',               'EL1045', 'classic', '#a59d90' ],
			[ 'white-ticino-oak',        'new-minimalism',   'Дуб Тичино',    'Белый',              'Дуб Цічына',      'Белы',               'EL1040', 'classic', '#e6ddcf' ],
			[ 'white-sherman-oak',       'new-minimalism',   'Дуб Шерман',    'Белый',              'Дуб Шэрман',      'Белы',               'EL1054', 'classic', '#ebe4d8' ],
			[ 'marble-light',            'new-minimalism',   'Мрамор',        'Светлый',            'Мармур',          'Светлы',             'EL1000', 'large',   '#ece9e4' ],
			[ 'marble-grey',             'new-minimalism',   'Мрамор',        'Серый',              'Мармур',          'Шэры',               'EL1002', 'large',   '#9c9a97' ],
			// Тихая роскошь
			[ 'natural-victoria-oak',    'quiet-luxury',     'Дуб Виктория',  'Натуральный',        'Дуб Вікторыя',    'Натуральны',         'EL1052', 'classic', '#a8835c' ],
			[ 'natural-virdia-oak',      'quiet-luxury',     'Дуб Вирдиа',    'Натуральный',        'Дуб Вірдыя',      'Натуральны',         'EL1038', 'classic', '#9e7a54' ],
			[ 'brown-virdia-oak',        'quiet-luxury',     'Дуб Вирдиа',    'Коричневый',         'Дуб Вірдыя',      'Карычневы',          'EL1039', 'classic', '#6b4f38' ],
			[ 'natural-casella-oak',     'quiet-luxury',     'Дуб Каселла',   'Натуральный',        'Дуб Касела',      'Натуральны',         'EL2152', 'classic', '#a47e57' ],
			[ 'brown-casella-oak',       'quiet-luxury',     'Дуб Каселла',   'Коричневый',         'Дуб Касела',      'Карычневы',          'EL2153', 'classic', '#5e4532' ],
			[ 'natural-lavaredo-oak',    'quiet-luxury',     'Дуб Лаваредо',  'Натуральный',        'Дуб Лаварэда',     'Натуральны',         'EL1047', 'classic', '#a07c58' ],
			[ 'brown-lavaredo-oak',      'quiet-luxury',     'Дуб Лаваредо',  'Коричневый',         'Дуб Лаварэда',     'Карычневы',          'EL1048', 'classic', '#634a36' ],
			[ 'natural-ticino-oak',      'quiet-luxury',     'Дуб Тичино',    'Натуральный',        'Дуб Цічына',      'Натуральны',         'EL1043', 'classic', '#a8845e' ],
			[ 'brown-ticino-oak',        'quiet-luxury',     'Дуб Тичино',    'Коричневый',         'Дуб Цічына',      'Карычневы',          'EL1044', 'classic', '#5a4232' ],
			[ 'turin-oak',               'quiet-luxury',     'Дуб Турин',     '',                   'Дуб Турын',       '',                   'EL2190', 'classic', '#2f2b28' ],
			// Природная эстетика
			[ 'light-natural-victoria-oak', 'nature-aesthetic', 'Дуб Виктория', 'Натуральный светлый', 'Дуб Вікторыя', 'Натуральны светлы', 'EL1051', 'classic', '#c9ab86' ],
			[ 'light-virdia-oak',        'nature-aesthetic', 'Дуб Вирдиа',    'Светлый',            'Дуб Вірдыя',      'Светлы',             'EL1036', 'classic', '#d3bb99' ],
			[ 'light-natural-virdia-oak', 'nature-aesthetic', 'Дуб Вирдиа',   'Натуральный светлый', 'Дуб Вірдыя',     'Натуральны светлы',  'EL1037', 'classic', '#c4a37c' ],
			[ 'white-casella-oak',       'nature-aesthetic', 'Дуб Каселла',   'Белый',              'Дуб Касела',      'Белы',               'EL2150', 'classic', '#e4dacb' ],
			[ 'light-natural-casella-oak', 'nature-aesthetic', 'Дуб Каселла', 'Натуральный светлый', 'Дуб Касела',     'Натуральны светлы',  'EL2151', 'classic', '#c8a982' ],
			[ 'light-natural-lavaredo-oak', 'nature-aesthetic', 'Дуб Лаваредо', 'Натуральный светлый', 'Дуб Лаварэда',  'Натуральны светлы',  'EL1046', 'classic', '#c6a680' ],
			[ 'light-padua-oak',         'nature-aesthetic', 'Дуб Падуа',     'Светлый',            'Дуб Падуя',       'Светлы',             'EL2170', 'classic', '#d6c0a0' ],
			[ 'natural-padua-oak',       'nature-aesthetic', 'Дуб Падуа',     'Натуральный',        'Дуб Падуя',       'Натуральны',         'EL2171', 'classic', '#b08b63' ],
			[ 'grey-padua-oak',          'nature-aesthetic', 'Дуб Падуа',     'Серый',              'Дуб Падуя',       'Шэры',               'EL2173', 'classic', '#9f968a' ],
			[ 'light-natural-ticino-oak', 'nature-aesthetic', 'Дуб Тичино',   'Натуральный светлый', 'Дуб Цічына',     'Натуральны светлы',  'EL1041', 'classic', '#c9aa83' ],
		]
	),
];
