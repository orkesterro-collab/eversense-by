<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-hero ev-dark" data-slider data-autoplay="7000" aria-roledescription="carousel" aria-label="EVERSENSE">
	<div class="ev-hero__slides">
		<?php foreach ( [ 1, 2, 3 ] as $i ) : ?>
			<div class="ev-hero__slide<?php echo 1 === $i ? ' is-active' : ''; ?>" data-slide aria-roledescription="slide" aria-label="<?php echo esc_attr( $i . ' / 3' ); ?>">
				<div class="ev-hero__bg"><?php echo ev_media( 'img_hero_' . $i, [ 1 => 'warm', 2 => 'dark', 3 => 'rings' ][ $i ] ); // phpcs:ignore WordPress.Security.EscapeOutput ?></div>
				<div class="ev-container ev-hero__content">
					<p class="ev-hero__kicker"><?php ev_e( 'hero_kicker' ); ?></p>
					<?php if ( 1 === $i ) : ?>
						<h1 class="ev-hero__title"><?php ev_e( 'hero_title' ); ?></h1>
					<?php else : ?>
						<p class="ev-hero__title" aria-hidden="true"><?php ev_e( 'hero_title' ); ?></p>
					<?php endif; ?>
					<p class="ev-hero__text"><?php ev_e( 'hero_slide_' . $i ); ?></p>
					<a class="ev-btn ev-btn--light" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php ev_e( 'view_catalog' ); ?></a>
				</div>
			</div>
		<?php endforeach; ?>
	</div>
	<div class="ev-frame" aria-hidden="true"></div>
	<div class="ev-container ev-hero__controls">
		<div class="ev-dots" data-dots></div>
		<div class="ev-arrows">
			<button type="button" class="ev-arrow" data-prev><span class="ev-sr"><?php ev_e( 'prev' ); ?></span><?php echo ev_icon( 'arrow-l' ); // phpcs:ignore ?></button>
			<button type="button" class="ev-arrow" data-next><span class="ev-sr"><?php ev_e( 'next' ); ?></span><?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?></button>
		</div>
	</div>
</section>
