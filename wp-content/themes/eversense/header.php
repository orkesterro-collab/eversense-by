<?php defined( 'ABSPATH' ) || exit; ?>
<!doctype html>
<html <?php language_attributes(); ?> class="no-js">
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<script>document.documentElement.className = document.documentElement.className.replace("no-js", "js");</script>
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<meta name="format-detection" content="telephone=no">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="ev-skip" href="#main"><?php echo esc_html( 'be' === ev_lang() ? 'Да зместу' : 'К содержанию' ); ?></a>

<header class="ev-header" data-header>
	<div class="ev-container ev-header__inner">
		<nav class="ev-header__nav" aria-label="<?php echo esc_attr( ev_t( 'menu_catalog' ) ); ?>">
			<?php foreach ( array_slice( ev_nav_items(), 0, 2 ) as $item ) : ?>
				<a class="ev-header__link<?php echo $item['active'] ? ' is-active' : ''; ?>" href="<?php echo esc_url( $item['url'] ); ?>"><?php echo esc_html( $item['label'] ); ?></a>
			<?php endforeach; ?>
		</nav>

		<a class="ev-logo" href="<?php echo esc_url( ev_home_url() ); ?>" aria-label="EVERSENSE — <?php echo esc_attr( ev_t( 'home' ) ); ?>">
			<?php echo ev_logo(); // phpcs:ignore WordPress.Security.EscapeOutput ?>
		</a>

		<div class="ev-header__right">
			<a class="ev-header__link ev-header__contacts" href="<?php echo esc_url( ev_home_url( '#contacts' ) ); ?>"><?php ev_e( 'menu_contacts' ); ?></a>
			<div class="ev-lang" role="navigation" aria-label="Language">
				<?php foreach ( ev_language_links() as $i => $l ) : ?>
					<?php if ( $i ) : ?><span class="ev-lang__sep" aria-hidden="true">/</span><?php endif; ?>
					<?php if ( $l['current'] ) : ?>
						<span class="ev-lang__item is-current" aria-current="true"><?php echo esc_html( $l['short'] ); ?></span>
					<?php else : ?>
						<a class="ev-lang__item" href="<?php echo esc_url( $l['url'] ); ?>" hreflang="<?php echo esc_attr( $l['slug'] ); ?>" lang="<?php echo esc_attr( $l['slug'] ); ?>"><?php echo esc_html( $l['short'] ); ?></a>
					<?php endif; ?>
				<?php endforeach; ?>
			</div>
			<button class="ev-burger" type="button" aria-expanded="false" aria-controls="ev-drawer" data-drawer-open>
				<span class="ev-sr"><?php ev_e( 'menu_open' ); ?></span>
				<?php echo ev_icon( 'menu' ); // phpcs:ignore WordPress.Security.EscapeOutput ?>
			</button>
		</div>
	</div>
</header>

<div class="ev-drawer" id="ev-drawer" hidden data-drawer>
	<div class="ev-drawer__panel">
		<div class="ev-drawer__top">
			<a class="ev-logo" href="<?php echo esc_url( ev_home_url() ); ?>"><?php echo ev_logo( 'full' ); // phpcs:ignore WordPress.Security.EscapeOutput ?></a>
			<button class="ev-drawer__close" type="button" data-drawer-close>
				<span class="ev-sr"><?php ev_e( 'menu_close' ); ?></span>
				<?php echo ev_icon( 'close' ); // phpcs:ignore WordPress.Security.EscapeOutput ?>
			</button>
		</div>
		<nav class="ev-drawer__nav">
			<?php foreach ( ev_nav_items() as $item ) : ?>
				<a href="<?php echo esc_url( $item['url'] ); ?>" data-drawer-close><?php echo esc_html( $item['label'] ); ?></a>
			<?php endforeach; ?>
		</nav>
		<div class="ev-drawer__bottom">
			<div class="ev-lang">
				<?php foreach ( ev_language_links() as $i => $l ) : ?>
					<?php if ( $i ) : ?><span class="ev-lang__sep" aria-hidden="true">/</span><?php endif; ?>
					<a class="ev-lang__item<?php echo $l['current'] ? ' is-current' : ''; ?>" href="<?php echo esc_url( $l['url'] ); ?>"><?php echo esc_html( $l['short'] ); ?></a>
				<?php endforeach; ?>
			</div>
			<?php if ( ev_opt( 'phone' ) ) : ?>
				<a class="ev-drawer__phone" href="<?php echo esc_attr( ev_tel( ev_opt( 'phone' ) ) ); ?>"><?php echo esc_html( ev_opt( 'phone' ) ); ?></a>
			<?php endif; ?>
			<?php get_template_part( 'template-parts/social' ); ?>
		</div>
	</div>
</div>

<main id="main" class="ev-main">
