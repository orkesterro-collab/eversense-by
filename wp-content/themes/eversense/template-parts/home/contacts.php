<?php
defined( 'ABSPATH' ) || exit;
$places = array_filter(
	[
		'contacts_office'    => ev_opt_l( 'office' ),
		'contacts_warehouse' => ev_opt_l( 'warehouse' ),
	]
);
$first  = reset( $places );
?>
<section class="ev-contacts ev-section" id="contacts">
	<div class="ev-container">
		<h2 class="ev-h2" data-reveal><?php ev_e( 'contacts_title' ); ?></h2>
		<div class="ev-contacts__grid">
			<div class="ev-contacts__info" data-reveal>
				<?php if ( ev_opt_l( 'company' ) ) : ?>
					<p class="ev-contacts__company"><?php echo esc_html( ev_opt_l( 'company' ) ); ?></p>
				<?php endif; ?>

				<?php foreach ( $places as $label => $address ) : ?>
					<div class="ev-contacts__row">
						<?php echo ev_icon( 'pin' ); // phpcs:ignore ?>
						<div>
							<p class="ev-contacts__label"><?php ev_e( $label ); ?></p>
							<a href="<?php echo esc_url( 'https://yandex.by/maps/?text=' . rawurlencode( $address ) ); ?>" target="_blank" rel="noopener"><?php echo esc_html( $address ); ?></a>
						</div>
					</div>
				<?php endforeach; ?>

				<?php if ( ev_opt( 'phone' ) ) : ?>
					<div class="ev-contacts__row">
						<?php echo ev_icon( 'phone' ); // phpcs:ignore ?>
						<div>
							<p class="ev-contacts__label"><?php ev_e( 'contacts_phone' ); ?></p>
							<a href="<?php echo esc_attr( ev_tel( ev_opt( 'phone' ) ) ); ?>"><?php echo esc_html( ev_opt( 'phone' ) ); ?></a>
							<?php if ( ev_opt( 'phone_2' ) ) : ?>
								<br><a href="<?php echo esc_attr( ev_tel( ev_opt( 'phone_2' ) ) ); ?>"><?php echo esc_html( ev_opt( 'phone_2' ) ); ?></a>
							<?php endif; ?>
						</div>
					</div>
				<?php endif; ?>

				<?php if ( ev_opt( 'email' ) ) : ?>
					<div class="ev-contacts__row">
						<?php echo ev_icon( 'mail' ); // phpcs:ignore ?>
						<div>
							<p class="ev-contacts__label"><?php ev_e( 'contacts_email' ); ?></p>
							<a href="mailto:<?php echo esc_attr( ev_opt( 'email' ) ); ?>"><?php echo esc_html( ev_opt( 'email' ) ); ?></a>
						</div>
					</div>
				<?php endif; ?>

				<?php if ( ev_opt_l( 'hours' ) ) : ?>
					<div class="ev-contacts__row">
						<?php echo ev_icon( 'clock' ); // phpcs:ignore ?>
						<div>
							<p class="ev-contacts__label"><?php ev_e( 'contacts_hours' ); ?></p>
							<span><?php echo esc_html( ev_opt_l( 'hours' ) ); ?></span>
						</div>
					</div>
				<?php endif; ?>

				<?php get_template_part( 'template-parts/social' ); ?>
			</div>

			<div class="ev-contacts__map ev-framed" data-reveal>
				<?php if ( $first ) : ?>
					<iframe title="<?php echo esc_attr( ev_t( 'contacts_title' ) ); ?>" loading="lazy" src="<?php echo esc_url( 'https://yandex.by/map-widget/v1/?text=' . rawurlencode( $first ) . '&z=15&lang=' . ( 'be' === ev_lang() ? 'be_BY' : 'ru_RU' ) ); ?>"></iframe>
				<?php else : ?>
					<div class="ev-art ev-art--light"></div>
				<?php endif; ?>
			</div>
		</div>
	</div>
</section>
