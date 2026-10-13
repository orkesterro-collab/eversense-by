<?php
/**
 * Вспомогательные функции: страна, язык, тексты, настройки, ссылки.
 */

defined( 'ABSPATH' ) || exit;

/** Код страны сайта: by | kz. */
function ev_country_code() {
	$code = defined( 'EVERSENSE_COUNTRY' ) ? strtolower( (string) EVERSENSE_COUNTRY ) : 'by';
	$all  = ev_countries();
	return isset( $all[ $code ] ) ? $code : 'by';
}

/** Все страны из config/countries.php. */
function ev_countries() {
	static $all = null;
	if ( null === $all ) {
		$all = require EV_DIR . '/config/countries.php';
	}
	return $all;
}

/** Настройки текущей страны. */
function ev_country( $key = null ) {
	$c = ev_countries()[ ev_country_code() ];
	return null === $key ? $c : ( $c[ $key ] ?? null );
}

/** Языки текущей страны: [slug => [...]]. */
function ev_languages() {
	$out = [];
	foreach ( ev_country( 'languages' ) as $l ) {
		$out[ $l['slug'] ] = $l;
	}
	return $out;
}

/** Основной язык страны (первый в списке). */
function ev_default_lang() {
	$langs = ev_country( 'languages' );
	return $langs[0]['slug'];
}

/** Текущий язык страницы. */
function ev_lang() {
	if ( function_exists( 'pll_current_language' ) ) {
		$l = pll_current_language( 'slug' );
		if ( $l ) {
			return $l;
		}
	}
	return ev_default_lang();
}

/**
 * Текст интерфейса по ключу для текущего языка.
 * Порядок: lang/{язык}.php → lang/ru.php → сам ключ.
 */
function ev_t( $key, $lang = null ) {
	static $cache = [];
	$lang = $lang ?: ev_lang();
	foreach ( [ $lang, 'ru' ] as $l ) {
		if ( ! isset( $cache[ $l ] ) ) {
			$file        = EV_DIR . '/lang/' . sanitize_key( $l ) . '.php';
			$cache[ $l ] = is_readable( $file ) ? require $file : [];
		}
		if ( isset( $cache[ $l ][ $key ] ) ) {
			return $cache[ $l ][ $key ];
		}
	}
	return $key;
}

/** Экранированный вывод текста интерфейса. */
function ev_e( $key ) {
	echo esc_html( ev_t( $key ) );
}

/** Значения по умолчанию для настроек. */
function ev_option_defaults() {
	return array_merge(
		[
			'telegram'       => '',
			'instagram'      => '',
			'vk'             => '',
			'facebook'       => '',
			'textures_url'   => 'https://www.dl.dropboxusercontent.com/scl/fi/ppn59kjw3ja7bhz2m17to/EVERSENSE.zip?rlkey=0q6rnmewwg19lhkz569hxsybh&st=1jm00jz1&dl=0',
			'iso9001_url'    => 'https://drive.google.com/file/d/1WhH5i4aGF-HYs_H9qXDc33Fp8SG2l1TI/view',
			'iso14001_url'   => 'https://drive.google.com/file/d/1u0EbgLGx0wv7L6TCQtJCRolFvo6sdTzC/view',
			'booklet_1_url'  => 'https://drive.google.com/file/d/14UHdAfuU-TcMf7wgmzx7HoVyVgksjO8Y/view',
			'booklet_2_url'  => 'https://drive.google.com/file/d/12ttsTD0r0fEMeliofF_1HBsO2hCPzp29/view',
			'instruction_url'=> 'https://drive.google.com/file/d/1dImDaWKPtefl-TOjxHiSL3zauqBfHdJH/view',
			'video_1'        => 'https://dl.dropboxusercontent.com/scl/fi/krjo6dc5k2udyk2s99k7p/1.mp4?rlkey=8klwitb2169p0glx8ra3zsx3c&st=26e3j6vc&dl=0',
			'video_2'        => 'https://dl.dropboxusercontent.com/scl/fi/23w6rkj5wf6yp79bse0cg/2.mp4?rlkey=61of26ipcgx4uxlths6oanls5&st=fqta5ktm&dl=0',
			'yandex_key'     => '',
			'metrika_id'     => '',
			'show_award'     => '1',
		],
		(array) ev_country( 'defaults' )
	);
}

/** Настройка сайта (Внешний вид → Настройки EVERSENSE). */
function ev_opt( $key ) {
	static $opts = null;
	if ( null === $opts ) {
		$opts = wp_parse_args( (array) get_option( 'ev_settings', [] ), ev_option_defaults() );
	}
	return $opts[ $key ] ?? '';
}

/** Языковая настройка: office → office_be, если пусто — office_ru. */
function ev_opt_l( $key ) {
	$v = ev_opt( $key . '_' . ev_lang() );
	return '' !== $v ? $v : ev_opt( $key . '_' . ev_default_lang() );
}

/** Адрес главной в текущем языке. */
function ev_home_url( $path = '' ) {
	$home = function_exists( 'pll_home_url' ) ? pll_home_url( ev_lang() ) : home_url( '/' );
	return trailingslashit( $home ) . ltrim( $path, '/' );
}

/** Адрес каталога в текущем языке. */
function ev_catalog_url() {
	return ev_home_url( 'catalog/' );
}

/**
 * Адрес служебной страницы по её роли (where | privacy) в текущем языке.
 * Роль хранится в мета-поле _ev_role страницы.
 */
function ev_page_url( $role ) {
	static $cache = [];
	$lang = ev_lang();
	if ( ! isset( $cache[ $role ][ $lang ] ) ) {
		$args = [
			'post_type'   => 'page',
			'post_status' => 'publish',
			'meta_key'    => '_ev_role',
			'meta_value'  => $role,
			'numberposts' => 1,
			'fields'      => 'ids',
		];
		if ( function_exists( 'pll_current_language' ) ) {
			$args['lang'] = $lang;
		}
		$ids                    = get_posts( $args );
		$cache[ $role ][ $lang ] = $ids ? get_permalink( $ids[0] ) : ev_home_url();
	}
	return $cache[ $role ][ $lang ];
}

/** Ссылка на телефон. */
function ev_tel( $phone ) {
	return 'tel:' . preg_replace( '/[^0-9+]/', '', (string) $phone );
}

/** URL картинки из настроек (ID вложения) или пусто. */
function ev_image_url( $id, $size = 'full' ) {
	$id = absint( $id );
	return $id ? (string) wp_get_attachment_image_url( $id, $size ) : '';
}

/**
 * Фото из настроек или фирменная «деревянная» заглушка, пока фото не загружено.
 * $art — вариант заглушки: warm | dark | light | rings.
 */
function ev_media( $opt_key, $art = 'warm', $class = '', $size = 'ev-wide', $alt = '' ) {
	$id = absint( ev_opt( $opt_key ) );
	if ( $id ) {
		return wp_get_attachment_image( $id, $size, false, [ 'class' => 'ev-media-img ' . $class, 'loading' => 'lazy', 'alt' => $alt ] );
	}
	return '<div class="ev-art ev-art--' . esc_attr( $art ) . ' ' . esc_attr( $class ) . '" aria-hidden="true"></div>';
}

/** Видео mp4 из настроек (без звука, по кругу) или заглушка. */
function ev_video( $opt_key, $art = 'warm' ) {
	$url = ev_opt( $opt_key );
	if ( ! $url ) {
		return '<div class="ev-art ev-art--' . esc_attr( $art ) . '" aria-hidden="true"></div>';
	}
	return '<div class="ev-art ev-art--' . esc_attr( $art ) . '" aria-hidden="true"></div><video class="ev-video" muted loop playsinline preload="none" data-autoplay src="' . esc_url( $url ) . '"></video>';
}

/** Название декора: «Дуб Виктория натуральный». */
function ev_decor_title( $post = null ) {
	$post   = get_post( $post );
	$finish = (string) get_post_meta( $post->ID, 'ev_finish', true );
	$name   = get_the_title( $post );
	return trim( $name . ' ' . mb_strtolower( $finish ) );
}

/** Серия декора (первый термин ev_series) или null. */
function ev_decor_series( $post = null ) {
	$terms = get_the_terms( get_post( $post ), 'ev_series' );
	return ( $terms && ! is_wp_error( $terms ) ) ? $terms[0] : null;
}

/** Серии в порядке поля «Порядок». */
function ev_series_list() {
	$terms = get_terms(
		[
			'taxonomy'   => 'ev_series',
			'hide_empty' => false,
			'meta_key'   => 'ev_order',
			'orderby'    => 'meta_value_num',
			'order'      => 'ASC',
		]
	);
	return is_wp_error( $terms ) ? [] : $terms;
}

/** Цвет-заглушка декора для блока без фото. */
function ev_decor_tone( $post = null ) {
	$tone = (string) get_post_meta( get_post( $post )->ID, 'ev_tone', true );
	return preg_match( '/^#[0-9a-f]{6}$/i', $tone ) ? $tone : '#c0a58c';
}

/**
 * Визуал декора: фото (если загружено) или «деревянная» заглушка его цвета.
 */
function ev_decor_visual( $post = null, $size = 'large', $class = '' ) {
	$post = get_post( $post );
	if ( has_post_thumbnail( $post ) ) {
		return '<div class="ev-swatch ' . esc_attr( $class ) . '">' . get_the_post_thumbnail( $post, $size, [ 'loading' => 'lazy', 'alt' => esc_attr( ev_decor_title( $post ) ) ] ) . '</div>';
	}
	return '<div class="ev-swatch ev-swatch--tone ' . esc_attr( $class ) . '" style="--tone:' . esc_attr( ev_decor_tone( $post ) ) . '" role="img" aria-label="' . esc_attr( ev_decor_title( $post ) ) . '"></div>';
}
