<?php
/**
 * Крупная карточка серии: фото (или полоса из декоров серии), название, описание, кнопка.
 * $args: term, index.
 */
defined( 'ABSPATH' ) || exit;

$term  = $args['term'];
$index = (int) ( $args['index'] ?? 0 );
$img   = absint( get_term_meta( $term->term_id, 'ev_image', true ) );
$link  = get_term_link( $term );
$decor = get_posts(
	[
		'post_type'   => 'ev_decor',
		'numberposts' => 6,
		'orderby'     => 'menu_order',
		'order'       => 'ASC',
		'tax_query'   => [ [ 'taxonomy' => 'ev_series', 'terms' => $term->term_id ] ], // phpcs:ignore WordPress.DB.SlowDBQuery
	]
);
?>
<article class="ev-series<?php echo $index % 2 ? ' ev-series--reverse' : ''; ?>" data-reveal>
	<a class="ev-series__media ev-framed" href="<?php echo esc_url( $link ); ?>" tabindex="-1" aria-hidden="true">
		<?php if ( $img ) : ?>
			<?php echo wp_get_attachment_image( $img, 'ev-wide', false, [ 'loading' => 'lazy', 'alt' => '' ] ); ?>
		<?php else : ?>
			<span class="ev-boards">
				<?php foreach ( $decor as $d ) : ?>
					<span class="ev-boards__plank" style="--tone:<?php echo esc_attr( ev_decor_tone( $d ) ); ?>">
						<?php if ( has_post_thumbnail( $d ) ) : ?>
							<?php echo get_the_post_thumbnail( $d, 'ev-card', [ 'loading' => 'lazy', 'alt' => '' ] ); ?>
						<?php endif; ?>
					</span>
				<?php endforeach; ?>
			</span>
		<?php endif; ?>
	</a>
	<div class="ev-series__body">
		<p class="ev-eyebrow"><?php ev_e( 'series' ); ?></p>
		<h3 class="ev-h2"><a href="<?php echo esc_url( $link ); ?>"><?php echo esc_html( $term->name ); ?></a></h3>
		<?php if ( get_term_meta( $term->term_id, 'ev_lead', true ) ) : ?>
			<p class="ev-lead"><?php echo esc_html( get_term_meta( $term->term_id, 'ev_lead', true ) ); ?></p>
		<?php endif; ?>
		<?php if ( get_term_meta( $term->term_id, 'ev_text', true ) ) : ?>
			<p><?php echo esc_html( get_term_meta( $term->term_id, 'ev_text', true ) ); ?></p>
		<?php endif; ?>
		<?php if ( $decor ) : ?>
			<ul class="ev-tones" aria-hidden="true">
				<?php foreach ( $decor as $d ) : ?>
					<li style="--tone:<?php echo esc_attr( ev_decor_tone( $d ) ); ?>"></li>
				<?php endforeach; ?>
			</ul>
		<?php endif; ?>
		<a class="ev-btn" href="<?php echo esc_url( $link ); ?>"><?php ev_e( 'view_catalog' ); ?></a>
	</div>
</article>
