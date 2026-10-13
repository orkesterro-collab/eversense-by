<?php
/**
 * Типы контента: декоры (каталог), серии, дилеры.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'init',
	static function () {
		register_post_type(
			'ev_decor',
			[
				'labels'        => [
					'name'          => 'Декоры',
					'singular_name' => 'Декор',
					'add_new'       => 'Добавить декор',
					'add_new_item'  => 'Новый декор',
					'edit_item'     => 'Редактировать декор',
					'all_items'     => 'Все декоры',
					'menu_name'     => 'Каталог',
				],
				'public'        => true,
				'has_archive'   => 'catalog',
				'rewrite'       => [ 'slug' => 'catalog', 'with_front' => false ],
				'menu_icon'     => 'dashicons-grid-view',
				'menu_position' => 5,
				'supports'      => [ 'title', 'editor', 'thumbnail', 'page-attributes' ],
				'show_in_rest'  => true,
			]
		);

		register_taxonomy(
			'ev_series',
			[ 'ev_decor' ],
			[
				'labels'            => [
					'name'          => 'Серии',
					'singular_name' => 'Серия',
					'add_new_item'  => 'Новая серия',
					'edit_item'     => 'Редактировать серию',
					'menu_name'     => 'Серии',
				],
				'public'            => true,
				'hierarchical'      => true,
				'show_admin_column' => true,
				'show_in_rest'      => true,
				'rewrite'           => [ 'slug' => 'series', 'with_front' => false ],
			]
		);

		register_post_type(
			'ev_dealer',
			[
				'labels'        => [
					'name'          => 'Где купить',
					'singular_name' => 'Магазин',
					'add_new'       => 'Добавить магазин',
					'add_new_item'  => 'Новый магазин',
					'edit_item'     => 'Редактировать магазин',
					'all_items'     => 'Все магазины',
					'menu_name'     => 'Где купить',
				],
				'public'        => false,
				'show_ui'       => true,
				'menu_icon'     => 'dashicons-location',
				'menu_position' => 6,
				'supports'      => [ 'title', 'page-attributes' ],
			]
		);
	}
);

/** Декоры, серии и магазины переводятся через Polylang. */
add_filter(
	'pll_get_post_types',
	static function ( $types ) {
		$types['ev_decor']  = 'ev_decor';
		$types['ev_dealer'] = 'ev_dealer';
		return $types;
	}
);
add_filter(
	'pll_get_taxonomies',
	static function ( $tax ) {
		$tax['ev_series'] = 'ev_series';
		return $tax;
	}
);

/** Каталог и серии показываем целиком, по порядку. */
add_action(
	'pre_get_posts',
	static function ( $q ) {
		if ( is_admin() || ! $q->is_main_query() ) {
			return;
		}
		if ( $q->is_post_type_archive( 'ev_decor' ) || $q->is_tax( 'ev_series' ) ) {
			$q->set( 'posts_per_page', -1 );
			$q->set( 'orderby', [ 'menu_order' => 'ASC', 'title' => 'ASC' ] );
		}
	}
);

/** Колонки в списке декоров: артикул и фото. */
add_filter(
	'manage_ev_decor_posts_columns',
	static function ( $cols ) {
		$new = [];
		foreach ( $cols as $k => $v ) {
			if ( 'title' === $k ) {
				$new['ev_thumb'] = '';
			}
			$new[ $k ] = $v;
			if ( 'title' === $k ) {
				$new['ev_code']   = 'Артикул';
				$new['ev_finish'] = 'Отделка';
			}
		}
		return $new;
	}
);
add_action(
	'manage_ev_decor_posts_custom_column',
	static function ( $col, $id ) {
		if ( 'ev_thumb' === $col ) {
			echo has_post_thumbnail( $id )
				? get_the_post_thumbnail( $id, [ 48, 48 ] )
				: '<span style="display:block;width:48px;height:48px;border-radius:4px;background:' . esc_attr( ev_decor_tone( $id ) ) . '"></span>';
		}
		if ( 'ev_code' === $col ) {
			echo esc_html( get_post_meta( $id, 'ev_code', true ) );
		}
		if ( 'ev_finish' === $col ) {
			echo esc_html( get_post_meta( $id, 'ev_finish', true ) );
		}
	},
	10,
	2
);
add_action(
	'admin_head',
	static function () {
		echo '<style>.column-ev_thumb{width:56px}.column-ev_code{width:110px}</style>';
	}
);

/** Колонка «Город» у магазинов. */
add_filter(
	'manage_ev_dealer_posts_columns',
	static function ( $cols ) {
		return array_slice( $cols, 0, 2, true ) + [ 'ev_city' => 'Город', 'ev_address' => 'Адрес' ] + array_slice( $cols, 2, null, true );
	}
);
add_action(
	'manage_ev_dealer_posts_custom_column',
	static function ( $col, $id ) {
		if ( in_array( $col, [ 'ev_city', 'ev_address' ], true ) ) {
			echo esc_html( get_post_meta( $id, $col, true ) );
		}
	},
	10,
	2
);
