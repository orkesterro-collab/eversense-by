<?php
/** Карточка декора в сетке каталога. $args: post. */
defined( 'ABSPATH' ) || exit;
$p = get_post( $args['post'] ?? null );
?>
<li class="ev-card" data-reveal>
	<a class="ev-card__link" href="<?php echo esc_url( get_permalink( $p ) ); ?>">
		<?php echo ev_decor_visual( $p, 'ev-card', 'ev-card__img' ); // phpcs:ignore ?>
		<span class="ev-card__body">
			<span class="ev-card__name"><?php echo esc_html( get_the_title( $p ) ); ?></span>
			<?php if ( get_post_meta( $p->ID, 'ev_finish', true ) ) : ?>
				<span class="ev-card__finish"><?php echo esc_html( get_post_meta( $p->ID, 'ev_finish', true ) ); ?></span>
			<?php endif; ?>
			<span class="ev-card__code"><?php echo esc_html( get_post_meta( $p->ID, 'ev_code', true ) ); ?></span>
			<span class="ev-card__price"><?php echo ev_price_html( get_post_meta( $p->ID, 'ev_code', true ) ); // phpcs:ignore ?></span>
		</span>
	</a>
</li>
