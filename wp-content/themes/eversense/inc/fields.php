<?php
/**
 * Поля в админке: характеристики декора, данные магазина, описание серии.
 */

defined( 'ABSPATH' ) || exit;

/** Поля декора. */
function ev_decor_fields() {
	return [
		'ev_code'      => [ 'Артикул', 'text', 'EL1052' ],
		'ev_finish'    => [ 'Отделка (цвет)', 'text', 'Натуральный' ],
		'ev_tone'      => [ 'Цвет-заглушка (пока нет фото)', 'color', '#c0a58c' ],
		'ev_interior'  => [ 'Фото в интерьере', 'image', '' ],
		'ev_thickness' => [ 'Толщина', 'text', '8 мм' ],
		'ev_format'    => [ 'Формат', 'text', 'Classic' ],
		'ev_size'      => [ 'Размер', 'text', '1292 × 193 мм' ],
		'ev_lock'      => [ 'Тип замка', 'text', 'CLIC it!' ],
		'ev_chamfer'   => [ 'Тип фаски', 'text', 'V4' ],
		'ev_pack_pcs'  => [ 'Штук в упаковке', 'text', '8' ],
		'ev_pack_area' => [ 'Площадь в упаковке', 'text', '1,99 м²' ],
	];
}

/** Поля магазина. */
function ev_dealer_fields() {
	return [
		'ev_city'    => [ 'Город', 'text', 'Минск' ],
		'ev_address' => [ 'Адрес', 'text', 'ул. Примерная, 1' ],
		'ev_phone'   => [ 'Телефон', 'text', '+375 (29) 000-00-00' ],
		'ev_email'   => [ 'E-mail', 'text', '' ],
		'ev_site'    => [ 'Сайт', 'url', 'https://' ],
		'ev_hours'   => [ 'Режим работы', 'text', 'Пн–Сб 10:00–20:00' ],
		'ev_lat'     => [ 'Широта', 'text', '53.9006' ],
		'ev_lng'     => [ 'Долгота', 'text', '27.5590' ],
	];
}

/** Поля серии. */
function ev_series_fields() {
	return [
		'ev_lead'  => [ 'Короткое описание', 'textarea' ],
		'ev_text'  => [ 'Дополнительный текст', 'textarea' ],
		'ev_image' => [ 'Фото серии', 'image' ],
		'ev_order' => [ 'Порядок вывода', 'number' ],
	];
}

/** Вывод одного поля. */
function ev_render_field( $name, $type, $value, $placeholder = '' ) {
	$id   = esc_attr( trim( preg_replace( '/[^a-z0-9_]+/i', '_', $name ), '_' ) );
	$attr = esc_attr( $name );
	switch ( $type ) {
		case 'textarea':
			printf( '<textarea id="%1$s" name="%3$s" rows="3" class="large-text">%2$s</textarea>', $id, esc_textarea( $value ), $attr );
			break;
		case 'color':
			printf( '<input type="color" id="%1$s" name="%3$s" value="%2$s">', $id, esc_attr( $value ?: $placeholder ), $attr );
			break;
		case 'number':
			printf( '<input type="number" id="%1$s" name="%3$s" value="%2$s" class="small-text">', $id, esc_attr( $value ), $attr );
			break;
		case 'image':
			$url = ev_image_url( $value, 'medium' );
			printf(
				'<div class="ev-media"><input type="hidden" id="%1$s" name="%5$s" value="%2$s"><img src="%3$s" alt="" style="max-width:240px;display:%4$s;margin-bottom:6px;border-radius:4px"><br><button type="button" class="button ev-media-pick">Выбрать фото</button> <button type="button" class="button-link ev-media-clear">Убрать</button></div>',
				$id,
				esc_attr( $value ),
				esc_url( $url ),
				$url ? 'block' : 'none',
				$attr
			);
			break;
		default:
			printf( '<input type="%3$s" id="%1$s" name="%5$s" value="%2$s" placeholder="%4$s" class="regular-text">', $id, esc_attr( $value ), 'url' === $type ? 'url' : 'text', esc_attr( $placeholder ), $attr );
	}
}

/** Очистка значения поля. */
function ev_clean_field( $type, $raw ) {
	$raw = wp_unslash( $raw );
	switch ( $type ) {
		case 'textarea':
			return sanitize_textarea_field( $raw );
		case 'color':
			return sanitize_hex_color( $raw ) ?: '';
		case 'number':
		case 'image':
			return '' === $raw ? '' : (string) absint( $raw );
		case 'url':
			return esc_url_raw( $raw );
		default:
			return sanitize_text_field( $raw );
	}
}

add_action(
	'add_meta_boxes',
	static function () {
		add_meta_box( 'ev_decor_box', 'Характеристики декора', 'ev_meta_box', 'ev_decor', 'normal', 'high', [ 'fields' => ev_decor_fields() ] );
		add_meta_box( 'ev_dealer_box', 'Данные магазина', 'ev_meta_box', 'ev_dealer', 'normal', 'high', [ 'fields' => ev_dealer_fields() ] );
	}
);

function ev_meta_box( $post, $box ) {
	wp_nonce_field( 'ev_meta', 'ev_meta_nonce' );
	echo '<table class="form-table" role="presentation">';
	foreach ( $box['args']['fields'] as $name => $f ) {
		echo '<tr><th><label for="' . esc_attr( $name ) . '">' . esc_html( $f[0] ) . '</label></th><td>';
		ev_render_field( $name, $f[1], get_post_meta( $post->ID, $name, true ), $f[2] ?? '' );
		echo '</td></tr>';
	}
	echo '</table>';
	if ( 'ev_dealer' === $post->post_type ) {
		echo '<p class="description">Координаты можно взять в Яндекс Картах: правый клик по точке → «Что здесь?». Первое число — широта, второе — долгота.</p>';
	}
	if ( 'ev_decor' === $post->post_type ) {
		echo '<p class="description">Основное фото декора (текстура) — это «Изображение записи» справа. Серию выберите в блоке «Серии».</p>';
	}
}

add_action(
	'save_post',
	static function ( $post_id, $post ) {
		if ( ! isset( $_POST['ev_meta_nonce'] ) || ! wp_verify_nonce( sanitize_key( $_POST['ev_meta_nonce'] ), 'ev_meta' ) ) {
			return;
		}
		if ( ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) || ! current_user_can( 'edit_post', $post_id ) ) {
			return;
		}
		$fields = 'ev_decor' === $post->post_type ? ev_decor_fields() : ( 'ev_dealer' === $post->post_type ? ev_dealer_fields() : [] );
		foreach ( $fields as $name => $f ) {
			if ( isset( $_POST[ $name ] ) ) {
				update_post_meta( $post_id, $name, ev_clean_field( $f[1], $_POST[ $name ] ) ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput
			}
		}
	},
	10,
	2
);

/** Поля серии на странице добавления и редактирования. */
add_action(
	'ev_series_add_form_fields',
	static function () {
		wp_nonce_field( 'ev_meta', 'ev_meta_nonce' );
		foreach ( ev_series_fields() as $name => $f ) {
			echo '<div class="form-field"><label for="' . esc_attr( $name ) . '">' . esc_html( $f[0] ) . '</label>';
			ev_render_field( $name, $f[1], '' );
			echo '</div>';
		}
	}
);
add_action(
	'ev_series_edit_form_fields',
	static function ( $term ) {
		wp_nonce_field( 'ev_meta', 'ev_meta_nonce' );
		foreach ( ev_series_fields() as $name => $f ) {
			echo '<tr class="form-field"><th><label for="' . esc_attr( $name ) . '">' . esc_html( $f[0] ) . '</label></th><td>';
			ev_render_field( $name, $f[1], get_term_meta( $term->term_id, $name, true ) );
			echo '</td></tr>';
		}
	}
);
$ev_save_term = static function ( $term_id ) {
	if ( ! isset( $_POST['ev_meta_nonce'] ) || ! wp_verify_nonce( sanitize_key( $_POST['ev_meta_nonce'] ), 'ev_meta' ) || ! current_user_can( 'manage_categories' ) ) {
		return;
	}
	foreach ( ev_series_fields() as $name => $f ) {
		if ( isset( $_POST[ $name ] ) ) {
			update_term_meta( $term_id, $name, ev_clean_field( $f[1], $_POST[ $name ] ) ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput
		}
	}
};
add_action( 'created_ev_series', $ev_save_term );
add_action( 'edited_ev_series', $ev_save_term );

/** Выбор фото из медиатеки. */
add_action(
	'admin_enqueue_scripts',
	static function ( $hook ) {
		$screen = get_current_screen();
		$need   = $screen && ( in_array( $screen->post_type, [ 'ev_decor', 'ev_dealer' ], true ) || 'appearance_page_ev-settings' === $hook );
		if ( ! $need ) {
			return;
		}
		wp_enqueue_media();
		wp_enqueue_script( 'ev-admin', EV_URI . '/assets/js/admin.js', [ 'jquery' ], ev_asset_ver( 'assets/js/admin.js' ), true );
	}
);
