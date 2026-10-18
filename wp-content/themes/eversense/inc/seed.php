<?php
/**
 * WP-CLI: wp eversense seed
 * Создаёт языки Polylang, страницы, серии, декоры и примеры магазинов.
 * Повторный запуск ничего не дублирует: существующие записи пропускаются.
 */

defined( 'ABSPATH' ) || exit;

class EV_Seed_Command {

	/** @var array<string,string> */
	private $langs = [];

	/**
	 * Заполнить сайт стартовым контентом.
	 *
	 * ## EXAMPLES
	 *     wp eversense seed
	 */
	public function seed() {
		$this->languages();
		$catalog = require EV_DIR . '/data/catalog.php';
		$pages   = require EV_DIR . '/data/pages.php';

		$series = $this->series( $catalog['series'] );
		$this->decors( $catalog['decors'], $series );
		$this->pages( $pages );
		// Не добавляем вымышленные магазины. Заполняем список только проверенными партнёрами.

		if ( false === get_option( 'ev_settings', false ) ) {
			add_option( 'ev_settings', ev_option_defaults() );
		}
		WP_CLI::success( 'Контент EVERSENSE создан.' );
	}

	/** Языки страны в Polylang + настройки адресов. */
	private function languages() {
		if ( ! function_exists( 'PLL' ) || ! PLL() || ! isset( PLL()->model ) ) {
			WP_CLI::error( 'Polylang не активирован.' );
		}
		$model    = PLL()->model;
		$existing = wp_list_pluck( $model->get_languages_list(), 'slug' );
		$order    = 0;
		foreach ( ev_country( 'languages' ) as $l ) {
			$this->langs[ $l['slug'] ] = $l['slug'];
			if ( in_array( $l['slug'], $existing, true ) ) {
				continue;
			}
			$args = [
				'name'       => $l['name'],
				'slug'       => $l['slug'],
				'locale'     => $l['locale'],
				'rtl'        => 0,
				'term_group' => $order++,
				'flag'       => $l['flag'],
			];
			$res = ( isset( $model->languages ) && is_object( $model->languages ) && method_exists( $model->languages, 'add' ) )
				? $model->languages->add( $args )
				: $model->add_language( $args );
			if ( is_wp_error( $res ) ) {
				WP_CLI::warning( 'Язык ' . $l['slug'] . ': ' . $res->get_error_message() );
			} else {
				WP_CLI::log( 'Язык добавлен: ' . $l['name'] );
			}
			if ( 'ru_RU' !== $l['locale'] ) {
				// Переводы админки и плагина, если доступны.
				WP_CLI::runcommand( 'language core install ' . $l['locale'], [ 'return' => true, 'exit_error' => false ] );
				WP_CLI::runcommand( 'language plugin install polylang ' . $l['locale'], [ 'return' => true, 'exit_error' => false ] );
			}
		}

		$opts                  = get_option( 'polylang', [] );
		$opts['default_lang']  = ev_default_lang();
		$opts['force_lang']    = 1; // язык в адресе: /be/…
		$opts['hide_default']  = 1; // основной язык без префикса
		$opts['rewrite']       = 1; // без /language/
		$opts['browser']       = 0; // не угадывать язык по браузеру
		$opts['redirect_lang'] = 0;
		$opts['media_support'] = 0;
		$opts['post_types']    = array_values( array_unique( array_merge( (array) ( $opts['post_types'] ?? [] ), [ 'ev_decor', 'ev_dealer', 'ev_project', 'ev_installer' ] ) ) );
		$opts['taxonomies']    = array_values( array_unique( array_merge( (array) ( $opts['taxonomies'] ?? [] ), [ 'ev_series' ] ) ) );
		update_option( 'polylang', $opts );

		if ( method_exists( $model, 'clean_languages_cache' ) ) {
			$model->clean_languages_cache();
		}
	}

	/** Суффикс адреса для неосновного языка: slug-be. */
	private function slug( $slug, $lang ) {
		return ev_default_lang() === $lang ? $slug : $slug . '-' . $lang;
	}

	/** Серии во всех языках. Возвращает [slug => [lang => term_id]]. */
	private function series( $data ) {
		$out = [];
		foreach ( $data as $slug => $s ) {
			$ids = [];
			foreach ( $this->langs as $lang ) {
				$src = $s[ $lang ] ?? $s['ru'];
				$ts  = $this->slug( $slug, $lang );
				$t   = get_term_by( 'slug', $ts, 'ev_series' );
				if ( $t ) {
					$ids[ $lang ] = (int) $t->term_id;
					continue;
				}
				$r = wp_insert_term( $src['name'], 'ev_series', [ 'slug' => $ts ] );
				if ( is_wp_error( $r ) ) {
					WP_CLI::warning( 'Серия ' . $ts . ': ' . $r->get_error_message() );
					continue;
				}
				$id = (int) $r['term_id'];
				pll_set_term_language( $id, $lang );
				update_term_meta( $id, 'ev_lead', $src['lead'] );
				update_term_meta( $id, 'ev_text', $src['text'] );
				update_term_meta( $id, 'ev_order', (string) $s['order'] );
				$ids[ $lang ] = $id;
			}
			if ( count( $ids ) > 1 ) {
				pll_save_term_translations( $ids );
			}
			$out[ $slug ] = $ids;
			WP_CLI::log( 'Серия: ' . $s['ru']['name'] );
		}
		return $out;
	}

	private function decors( $decors, $series ) {
		$created = 0;
		foreach ( $decors as $i => $d ) {
			$ids = [];
			foreach ( $this->langs as $lang ) {
				$src  = $d[ $lang ] ?? $d['ru'];
				$slug = $this->slug( $d['slug'], $lang );
				$have = get_page_by_path( $slug, OBJECT, 'ev_decor' );
				if ( $have ) {
					$ids[ $lang ] = $have->ID;
					continue;
				}
				$id = wp_insert_post(
					[
						'post_type'   => 'ev_decor',
						'post_status' => 'publish',
						'post_title'  => $src['name'],
						'post_name'   => $slug,
						'menu_order'  => $i,
					],
					true
				);
				if ( is_wp_error( $id ) ) {
					WP_CLI::warning( $slug . ': ' . $id->get_error_message() );
					continue;
				}
				pll_set_post_language( $id, $lang );
				update_post_meta( $id, 'ev_code', $d['code'] );
				update_post_meta( $id, 'ev_finish', $src['finish'] );
				update_post_meta( $id, 'ev_tone', $d['tone'] );
				foreach ( $d['specs'] as $k => $v ) {
					update_post_meta( $id, 'ev_' . $k, $v );
				}
				if ( isset( $series[ $d['series'] ][ $lang ] ) ) {
					wp_set_object_terms( $id, [ $series[ $d['series'] ][ $lang ] ], 'ev_series' );
				}
				$ids[ $lang ] = $id;
				++$created;
			}
			if ( count( $ids ) > 1 ) {
				pll_save_post_translations( $ids );
			}
		}
		WP_CLI::log( 'Декоров создано: ' . $created );
	}

	private function pages( $pages ) {
		foreach ( [ 'home', 'where', 'privacy', 'warranty', 'installation' ] as $role ) {
			$p   = $pages[ $role ];
			$ids = [];
			foreach ( $this->langs as $lang ) {
				$src  = $p[ $lang ] ?? $p['ru'];
				$have = get_page_by_path( $src['slug'], OBJECT, 'page' );
				if ( $have ) {
					$ids[ $lang ] = $have->ID;
					continue;
				}
				$id = wp_insert_post(
					[
						'post_type'    => 'page',
						'post_status'  => 'publish',
						'post_title'   => $src['title'],
						'post_name'    => $src['slug'],
						'post_content' => $src['content'],
					],
					true
				);
				if ( is_wp_error( $id ) ) {
					WP_CLI::warning( $src['slug'] . ': ' . $id->get_error_message() );
					continue;
				}
				pll_set_post_language( $id, $lang );
				update_post_meta( $id, '_ev_role', $role );
				if ( ! empty( $p['template'] ) ) {
					update_post_meta( $id, '_wp_page_template', $p['template'] );
				}
				$ids[ $lang ] = $id;
			}
			if ( count( $ids ) > 1 ) {
				pll_save_post_translations( $ids );
			}
			if ( 'home' === $role && isset( $ids[ ev_default_lang() ] ) ) {
				update_option( 'show_on_front', 'page' );
				update_option( 'page_on_front', $ids[ ev_default_lang() ] );
			}
			if ( 'privacy' === $role && isset( $ids[ ev_default_lang() ] ) ) {
				update_option( 'wp_page_for_privacy_policy', $ids[ ev_default_lang() ] );
			}
			WP_CLI::log( 'Страница: ' . $p['ru']['title'] );
		}

		// Стандартные «Пример страницы» и «Привет, мир!» не нужны.
		foreach ( [ [ 'sample-page', 'page' ], [ 'hello-world', 'post' ] ] as [ $slug, $type ] ) {
			$p = get_page_by_path( $slug, OBJECT, $type );
			if ( $p ) {
				wp_delete_post( $p->ID, true );
			}
		}
	}

	private function dealers( $dealers ) {
		if ( get_posts( [ 'post_type' => 'ev_dealer', 'post_status' => 'any', 'numberposts' => 1, 'lang' => '' ] ) ) {
			return; // магазины уже есть — не трогаем
		}
		foreach ( $dealers as $i => $d ) {
			$ids = [];
			foreach ( $this->langs as $lang ) {
				$src = $d[ $lang ] ?? $d['ru'];
				$id  = wp_insert_post(
					[
						'post_type'   => 'ev_dealer',
						'post_status' => 'publish',
						'post_title'  => $src['title'],
						'menu_order'  => $i,
					]
				);
				if ( ! $id || is_wp_error( $id ) ) {
					continue;
				}
				pll_set_post_language( $id, $lang );
				update_post_meta( $id, 'ev_city', $src['city'] );
				update_post_meta( $id, 'ev_address', $src['address'] );
				foreach ( $d['meta'] as $k => $v ) {
					update_post_meta( $id, $k, $v );
				}
				$ids[ $lang ] = $id;
			}
			if ( count( $ids ) > 1 ) {
				pll_save_post_translations( $ids );
			}
		}
		WP_CLI::log( 'Примеры магазинов добавлены — замените их реальными.' );
	}
}

WP_CLI::add_command( 'eversense', 'EV_Seed_Command' );
