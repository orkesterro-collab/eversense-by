<?php
/**
 * Поддержка темы, ассеты, мелкие доработки.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'after_setup_theme',
	static function () {
		add_theme_support( 'title-tag' );
		add_theme_support( 'post-thumbnails' );
		add_theme_support( 'html5', [ 'search-form', 'gallery', 'caption', 'style', 'script' ] );
		add_theme_support(
			'custom-logo',
			[
				'height'      => 64,
				'width'       => 320,
				'flex-height' => true,
				'flex-width'  => true,
			]
		);
		add_image_size( 'ev-card', 720, 900, true );
		add_image_size( 'ev-wide', 1920, 1080, false );
	}
);

/** Шрифт, стили, скрипты. */
add_action(
	'wp_enqueue_scripts',
	static function () {
		// Manrope: если в assets/fonts лежат файлы из бренд-бука — берём их, иначе Google Fonts.
		if ( file_exists( EV_DIR . '/assets/fonts/fonts.css' ) ) {
			wp_enqueue_style( 'ev-fonts', EV_URI . '/assets/fonts/fonts.css', [], EV_VERSION );
		} else {
			wp_enqueue_style( 'ev-fonts', 'https://fonts.googleapis.com/css2?family=Manrope:wght@200;300;400;500;600;700;800&display=swap&subset=cyrillic', [], null );
		}
		wp_enqueue_style( 'ev-main', EV_URI . '/assets/css/main.css', [ 'ev-fonts' ], ev_asset_ver( 'assets/css/main.css' ) );
		wp_enqueue_script( 'ev-main', EV_URI . '/assets/js/main.js', [], ev_asset_ver( 'assets/js/main.js' ), true );

		if ( is_page() && 'where' === get_post_meta( get_queried_object_id(), '_ev_role', true ) ) {
			$key = ev_opt( 'yandex_key' );
			$src = 'https://api-maps.yandex.ru/2.1/?lang=' . ( 'be' === ev_lang() ? 'be_BY' : 'ru_RU' ) . ( $key ? '&apikey=' . rawurlencode( $key ) : '' );
			wp_enqueue_script( 'ev-ymaps', $src, [], null, true );
			wp_enqueue_script( 'ev-where', EV_URI . '/assets/js/where.js', [ 'ev-ymaps' ], ev_asset_ver( 'assets/js/where.js' ), true );
		}
	}
);

/** Версия файла по дате изменения — чтобы браузер не держал старый CSS. */
function ev_asset_ver( $rel ) {
	$f = EV_DIR . '/' . $rel;
	return file_exists( $f ) ? (string) filemtime( $f ) : EV_VERSION;
}

/** Предзагрузка шрифтов Google. */
add_action(
	'wp_head',
	static function () {
		if ( ! file_exists( EV_DIR . '/assets/fonts/fonts.css' ) ) {
			echo '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' . "\n";
		}
	},
	1
);

/** Описание страницы для поисковиков и соцсетей. */
add_action(
	'wp_head',
	static function () {
		if ( defined( 'WPSEO_VERSION' ) || defined( 'RANK_MATH_VERSION' ) ) {
			return; // SEO-плагин сам выведет метатеги.
		}
		$desc = ev_t( 'hero_title' ) . '. ' . ev_t( 'hero_slide_2' );
		if ( is_singular( 'ev_decor' ) ) {
			$s    = ev_decor_series();
			$desc = 'EVERSENSE' . ( $s ? ' «' . $s->name . '»' : '' ) . ' — ' . ev_decor_title() . ', ' . get_post_meta( get_the_ID(), 'ev_code', true );
		} elseif ( is_tax( 'ev_series' ) ) {
			$desc = (string) get_term_meta( get_queried_object_id(), 'ev_lead', true );
		}
		$img = has_post_thumbnail() && is_singular() ? get_the_post_thumbnail_url( null, 'ev-wide' ) : ev_image_url( ev_opt( 'img_hero_1' ), 'ev-wide' );
		echo '<meta name="description" content="' . esc_attr( wp_strip_all_tags( $desc ) ) . '">' . "\n";
		echo '<meta property="og:title" content="' . esc_attr( wp_get_document_title() ) . '">' . "\n";
		echo '<meta property="og:description" content="' . esc_attr( wp_strip_all_tags( $desc ) ) . '">' . "\n";
		echo '<meta property="og:type" content="website">' . "\n";
		if ( $img ) {
			echo '<meta property="og:image" content="' . esc_url( $img ) . '">' . "\n";
		}
		echo '<meta name="theme-color" content="#343333">' . "\n";
	},
	5
);

/** Яндекс Метрика, если указан номер счётчика. */
add_action(
	'wp_footer',
	static function () {
		$id = preg_replace( '/\D/', '', (string) ev_opt( 'metrika_id' ) );
		if ( ! $id ) {
			return;
		}
		?>
		<script>(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");ym(<?php echo (int) $id; ?>,"init",{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true});</script>
		<noscript><div><img src="https://mc.yandex.ru/watch/<?php echo (int) $id; ?>" style="position:absolute;left:-9999px" alt=""></div></noscript>
		<?php
	},
	99
);

/** Заголовок вкладки: «EVERSENSE | Каталог». */
add_filter(
	'document_title_separator',
	static function () {
		return '|';
	}
);
add_filter(
	'document_title_parts',
	static function ( $parts ) {
		if ( is_front_page() ) {
			return [ 'title' => 'EVERSENSE', 'tagline' => ev_t( 'home' ) ];
		}
		if ( is_post_type_archive( 'ev_decor' ) ) {
			$parts['title'] = ev_t( 'catalog_title' );
		}
		if ( is_singular( 'ev_decor' ) ) {
			$parts['title'] = ev_decor_title();
		}
		$parts['site'] = 'EVERSENSE';
		unset( $parts['tagline'] );
		return array_reverse( $parts );
	}
);

/** Убираем эмодзи-скрипты WordPress: они не нужны и замедляют страницу. */
remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
remove_action( 'wp_print_styles', 'print_emoji_styles' );

/** SVG-логотипы: загрузка разрешена только администраторам. */
add_filter(
	'upload_mimes',
	static function ( $m ) {
		if ( current_user_can( 'manage_options' ) ) {
			$m['svg'] = 'image/svg+xml';
		}
		return $m;
	}
);

/** Класс страницы для шапки поверх первого экрана. */
add_filter(
	'body_class',
	static function ( $c ) {
		if ( is_front_page() ) {
			$c[] = 'ev-has-hero';
		}
		return $c;
	}
);

/** Переключатель языков: [[slug, short, url, current], …]. */
function ev_language_links() {
	$langs = ev_languages();
	$out   = [];
	if ( function_exists( 'pll_the_languages' ) ) {
		$raw = pll_the_languages( [ 'raw' => 1, 'hide_if_empty' => 0, 'hide_if_no_translation' => 0 ] );
		foreach ( (array) $raw as $l ) {
			$out[] = [
				'slug'    => $l['slug'],
				'short'   => $langs[ $l['slug'] ]['short'] ?? strtoupper( $l['slug'] ),
				'url'     => $l['url'],
				'current' => ! empty( $l['current_lang'] ),
			];
		}
	}
	if ( ! $out ) {
		foreach ( $langs as $slug => $l ) {
			$out[] = [ 'slug' => $slug, 'short' => $l['short'], 'url' => home_url( '/' ), 'current' => ev_lang() === $slug ];
		}
	}
	return $out;
}

/** Пункты главного меню. */
function ev_nav_items() {
	return [
		[ 'label' => ev_t( 'menu_catalog' ), 'url' => ev_catalog_url(), 'active' => is_post_type_archive( 'ev_decor' ) || is_singular( 'ev_decor' ) || is_tax( 'ev_series' ) ],
		[ 'label' => ev_t( 'menu_where' ), 'url' => ev_page_url( 'where' ), 'active' => is_page() && 'where' === get_post_meta( get_queried_object_id(), '_ev_role', true ) ],
		[ 'label' => ev_t( 'menu_contacts' ), 'url' => ev_home_url( '#contacts' ), 'active' => false ],
	];
}

/** Логотип: загруженный в «Настройки → Логотип» или фирменное начертание текстом. */
function ev_logo( $variant = '' ) {
	$id = get_theme_mod( 'custom_logo' );
	if ( $id ) {
		return wp_get_attachment_image( $id, 'full', false, [ 'class' => 'ev-logo__img', 'alt' => 'EVERSENSE' ] );
	}
	return '<span class="ev-logo__word">EVERSENSE</span>'
		. ( 'full' === $variant ? '<span class="ev-logo__desc">' . esc_html( ev_t( 'brand_descriptor' ) ) . '</span>' : '' );
}
