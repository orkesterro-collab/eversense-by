<?php
/**
 * EVERSENSE Беларусь: проекты, укладчики и цены из Google Таблицы.
 * Данные клиентов и цены не выдумываются. Любые контакты и цены заполняются в админке.
 */
defined( 'ABSPATH' ) || exit;

add_action( 'init', static function () {
	register_post_type( 'ev_project', [
		'labels' => [ 'name' => 'Реализованные проекты', 'singular_name' => 'Проект', 'add_new_item' => 'Добавить проект', 'edit_item' => 'Редактировать проект' ],
		'public' => true, 'has_archive' => 'projects', 'rewrite' => [ 'slug' => 'projects' ],
		'show_in_rest' => true, 'menu_icon' => 'dashicons-format-gallery',
		'supports' => [ 'title', 'editor', 'thumbnail', 'excerpt' ],
	] );
	register_post_type( 'ev_installer', [
		'labels' => [ 'name' => 'Укладчики', 'singular_name' => 'Укладчик', 'add_new_item' => 'Добавить укладчика', 'edit_item' => 'Редактировать укладчика' ],
		'public' => true, 'has_archive' => 'installers', 'rewrite' => [ 'slug' => 'installers' ],
		'show_in_rest' => true, 'menu_icon' => 'dashicons-hammer',
		'supports' => [ 'title', 'editor', 'thumbnail' ],
	] );
}, 20 );

add_filter( 'pll_get_post_types', static function ( $types, $is_settings ) {
	$types['ev_project'] = 'ev_project';
	$types['ev_installer'] = 'ev_installer';
	return $types;
}, 10, 2 );

/** Управляемые поля для проекта и укладчика. */
add_action( 'add_meta_boxes', static function () {
	add_meta_box( 'ev-project-data', 'Связи с каталогом и фотографии', 'ev_project_meta_box', 'ev_project', 'normal' );
	add_meta_box( 'ev-installer-data', 'Контакты и проверка специалиста', 'ev_installer_meta_box', 'ev_installer', 'normal' );
} );

function ev_project_meta_box( $post ) {
	wp_nonce_field( 'ev_save_belarus', 'ev_belarus_nonce' );
	$code = get_post_meta( $post->ID, 'ev_related_codes', true );
	$imgs = get_post_meta( $post->ID, 'ev_gallery_ids', true );
	echo '<p><label>Артикулы декоров через запятую (например, EV123, EV456)<br><input style="width:100%" name="ev_related_codes" value="' . esc_attr( $code ) . '"></label></p>';
	echo '<p><label>ID фотографий из Медиатеки через запятую<br><input style="width:100%" name="ev_gallery_ids" value="' . esc_attr( $imgs ) . '"></label></p>';
	echo '<p>Обложка проекта: установите «Изображение записи». Описание редактируется в основном редакторе.</p>';
}
function ev_installer_meta_box( $post ) {
	wp_nonce_field( 'ev_save_belarus', 'ev_belarus_nonce' );
	foreach ( [ 'ev_city' => 'Город', 'ev_phone' => 'Телефон', 'ev_site' => 'Сайт или соцсеть' ] as $key => $label ) {
		echo '<p><label>' . esc_html( $label ) . '<br><input style="width:100%" name="' . esc_attr( $key ) . '" value="' . esc_attr( get_post_meta( $post->ID, $key, true ) ) . '"></label></p>';
	}
	echo '<p><label><input type="checkbox" name="ev_verified" value="1" ' . checked( get_post_meta( $post->ID, 'ev_verified', true ), '1', false ) . '> Статус специалиста проверен дистрибьютором; можно показывать отметку «Проверен»</label></p>';
	echo '<p>Публикуйте специалиста только с его согласия на размещение контактов.</p>';
}
add_action( 'save_post', static function ( $id ) {
	if ( ! isset( $_POST['ev_belarus_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['ev_belarus_nonce'] ) ), 'ev_save_belarus' ) || ! current_user_can( 'edit_post', $id ) || ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) ) {
		return;
	}
	if ( 'ev_project' === get_post_type( $id ) ) {
		foreach ( [ 'ev_related_codes', 'ev_gallery_ids' ] as $k ) {
			if ( isset( $_POST[$k] ) && is_string( $_POST[$k] ) ) {
				update_post_meta( $id, $k, sanitize_text_field( wp_unslash( $_POST[$k] ) ) );
			}
		}
	}
	if ( 'ev_installer' === get_post_type( $id ) ) {
		foreach ( [ 'ev_city', 'ev_phone', 'ev_site' ] as $k ) {
			if ( isset( $_POST[$k] ) && is_string( $_POST[$k] ) ) {
				$input = wp_unslash( $_POST[$k] );
				update_post_meta( $id, $k, 'ev_site' === $k ? esc_url_raw( $input ) : sanitize_text_field( $input ) );
			}
		}
		update_post_meta( $id, 'ev_verified', ! empty( $_POST['ev_verified'] ) ? '1' : '0' );
	}
} );

/** CSV Google Sheets: columns sku, price, sale_price, availability. Prices in BYN/m². */
function ev_prices_map() {
	$url = trim( (string) ev_opt( 'prices_csv_url' ) );
	$host = strtolower( (string) wp_parse_url( $url, PHP_URL_HOST ) );
	// Only official Google Sheets URLs. Never request arbitrary user-defined hosts.
	if ( ! in_array( $host, [ 'docs.google.com' ], true ) || ! preg_match( '~^https://docs\.google\.com/spreadsheets/d/(?:e/)?[a-zA-Z0-9_-]+/~', $url ) ) {
		return [];
	}
	$key = 'ev_prices_' . substr( md5( $url ), 0, 12 );
	$cached = get_transient( $key );
	if ( false !== $cached ) {
		return $cached;
	}
	$response = wp_safe_remote_get( $url, [ 'timeout' => 6, 'redirection' => 2, 'limit_response_size' => 1024 * 1024 ] );
	if ( is_wp_error( $response ) || 200 !== wp_remote_retrieve_response_code( $response ) ) {
		return [];
	}
	$body = wp_remote_retrieve_body( $response );
	$rows = preg_split( '/\r\n|\n|\r/', $body );
	if ( ! is_array( $rows ) || count( $rows ) < 2 ) {
		return [];
	}
	$first = preg_replace( '/^\xEF\xBB\xBF/', '', array_shift( $rows ) );
	$separator = substr_count( $first, ';' ) > substr_count( $first, ',' ) ? ';' : ',';
	$headers = array_map( static function ( $v ) {
		return mb_strtolower( trim( $v ) );
	}, str_getcsv( $first, $separator ) );
	$aliases = [
		'sku' => [ 'sku', 'code', 'article', 'артикул', 'код' ],
		'price' => [ 'price', 'regular_price', 'цена', 'обычная цена' ],
		'sale' => [ 'sale_price', 'promo_price', 'акция', 'акционная цена' ],
	];
	$idx = [];
	foreach ( $aliases as $key2 => $arr ) {
		foreach ( $arr as $candidate ) {
			$i = array_search( $candidate, $headers, true );
			if ( false !== $i ) { $idx[$key2] = $i; break; }
		}
	}
	if ( ! isset( $idx['sku'], $idx['price'] ) ) { return []; }
	$out = [];
	foreach ( $rows as $row ) {
		$cols = str_getcsv( $row, $separator );
		$code = trim( (string) ( $cols[$idx['sku']] ?? '' ) );
		if ( '' === $code ) { continue; }
		$normal = static function ( $v ) {
			$v = str_replace( [ ' ', "\xc2\xa0", ',' ], [ '', '', '.' ], (string) $v );
			return is_numeric( $v ) && (float) $v > 0 ? (float) $v : null;
		};
		$price = $normal( $cols[$idx['price']] ?? '' );
		$sale = isset( $idx['sale'] ) ? $normal( $cols[$idx['sale']] ?? '' ) : null;
		if ( null !== $price ) { $out[mb_strtoupper( $code )] = [ 'price' => $price, 'sale' => $sale && $sale < $price ? $sale : null ]; }
	}
	set_transient( $key, $out, 15 * MINUTE_IN_SECONDS );
	return $out;
}
function ev_decor_price( $code ) {
	$prices = ev_prices_map();
	return $prices[mb_strtoupper( trim( (string) $code ) )] ?? null;
}
function ev_price_html( $code ) {
	$p = ev_decor_price( $code );
	if ( ! $p ) {
		return '<span class="ev-price ev-price--pending">Цена уточняется</span>';
	}
	$regular = number_format( $p['price'], 2, ',', ' ' );
	if ( $p['sale'] ) {
		return '<span class="ev-price"><del>' . esc_html( $regular ) . ' BYN/м²</del><strong class="ev-price--sale">' . esc_html( number_format( $p['sale'], 2, ',', ' ' ) ) . ' BYN/м²</strong></span>';
	}
	return '<span class="ev-price"><strong>' . esc_html( $regular ) . ' BYN/м²</strong></span>';
}

function ev_projects_for_code( $code, $limit = 4 ) {
	$all = get_posts( [ 'post_type' => 'ev_project', 'posts_per_page' => 50, 'post_status' => 'publish', 'suppress_filters' => false ] );
	$matched = [];
	foreach ( $all as $project ) {
		$codes = preg_split( '/\s*[,;]\s*/', (string) get_post_meta( $project->ID, 'ev_related_codes', true ) );
		if ( in_array( mb_strtoupper( trim( $code ) ), array_map( 'mb_strtoupper', $codes ), true ) ) {
			$matched[] = $project;
			if ( count( $matched ) >= $limit ) { break; }
		}
	}
	return $matched;
}

add_action( 'admin_notices', static function () {
	if ( current_user_can( 'manage_options' ) && ! ev_opt( 'prices_csv_url' ) && isset( $_GET['page'] ) && 'ev-settings' === $_GET['page'] ) {
		echo '<div class="notice notice-info"><p>EVERSENSE: цены пока не подключены. Опубликуйте Google Таблицу в CSV и вставьте ссылку в раздел «Документы и файлы». Пустые цены на сайте не выдумываются.</p></div>';
	}
} );
