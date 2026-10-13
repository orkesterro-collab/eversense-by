<?php
/**
 * Карточка декора: фото, артикул, характеристики, преимущества, другие декоры серии.
 */
defined( 'ABSPATH' ) || exit;
get_header();

while ( have_posts() ) :
	the_post();
	$id     = get_the_ID();
	$series = ev_decor_series();
	$specs  = [
		'spec_thickness' => 'ev_thickness',
		'spec_format'    => 'ev_format',
		'spec_size'      => 'ev_size',
		'spec_lock'      => 'ev_lock',
		'spec_chamfer'   => 'ev_chamfer',
		'spec_pack_pcs'  => 'ev_pack_pcs',
		'spec_pack_area' => 'ev_pack_area',
	];
	$crumbs = [ [ ev_t( 'catalog_title' ), ev_catalog_url() ] ];
	if ( $series ) {
		$crumbs[] = [ $series->name, get_term_link( $series ) ];
	}
	$crumbs[] = [ ev_decor_title(), null ];
	$interior = absint( get_post_meta( $id, 'ev_interior', true ) );
	?>
	<article class="ev-decor ev-section--tight">
		<div class="ev-container">
			<?php get_template_part( 'template-parts/breadcrumbs', null, [ 'items' => $crumbs ] ); ?>

			<div class="ev-decor__grid">
				<div class="ev-decor__media">
					<?php echo ev_decor_visual( $id, 'ev-wide', 'ev-decor__swatch ev-framed' ); // phpcs:ignore ?>
					<?php if ( $interior ) : ?>
						<div class="ev-decor__interior ev-framed"><?php echo wp_get_attachment_image( $interior, 'ev-wide', false, [ 'alt' => esc_attr( ev_decor_title() ) ] ); ?></div>
					<?php endif; ?>
				</div>

				<div class="ev-decor__info">
					<?php if ( $series ) : ?>
						<a class="ev-eyebrow" href="<?php echo esc_url( get_term_link( $series ) ); ?>"><?php ev_e( 'series' ); ?> «<?php echo esc_html( $series->name ); ?>»</a>
					<?php endif; ?>
					<h1 class="ev-display ev-decor__title"><?php the_title(); ?></h1>
					<p class="ev-decor__finish">
						<?php echo esc_html( get_post_meta( $id, 'ev_finish', true ) ); ?>
						<span class="ev-decor__code"><?php ev_e( 'decor_code' ); ?> <?php echo esc_html( get_post_meta( $id, 'ev_code', true ) ); ?></span>
					</p>

					<?php if ( get_the_content() ) : ?>
						<div class="ev-prose"><?php the_content(); ?></div>
					<?php endif; ?>

					<h2 class="ev-h4"><?php ev_e( 'decor_specs' ); ?></h2>
					<dl class="ev-specs">
						<?php foreach ( $specs as $label => $key ) : ?>
							<?php $v = get_post_meta( $id, $key, true ); ?>
							<?php if ( '' !== (string) $v ) : ?>
								<div class="ev-specs__row">
									<dt><?php ev_e( $label ); ?></dt>
									<dd><?php echo esc_html( 'ev_pack_pcs' === $key && is_numeric( $v ) ? $v . ' ' . ev_t( 'unit_pcs' ) : $v ); ?></dd>
								</div>
							<?php endif; ?>
						<?php endforeach; ?>
					</dl>

					<h2 class="ev-h4"><?php ev_e( 'decor_advantages' ); ?></h2>
					<ul class="ev-adv">
						<?php foreach ( [ 1 => 'layers', 2 => 'shield', 3 => 'drop', 4 => 'impact' ] as $i => $icon ) : ?>
							<li><?php echo ev_icon( $icon ); // phpcs:ignore ?><span><?php ev_e( 'adv_' . $i ); ?></span></li>
						<?php endforeach; ?>
					</ul>

					<div class="ev-decor__cta">
						<p><?php ev_e( 'decor_where_text' ); ?></p>
						<a class="ev-btn" href="<?php echo esc_url( ev_page_url( 'where' ) ); ?>"><?php echo ev_icon( 'pin' ); // phpcs:ignore ?> <?php ev_e( 'decor_where_cta' ); ?></a>
					</div>

					<div class="ev-page-nav ev-page-nav--small">
						<a class="ev-link-arrow ev-link-arrow--back" href="<?php echo esc_url( $series ? get_term_link( $series ) : ev_catalog_url() ); ?>" data-back><?php echo ev_icon( 'arrow-l' ); // phpcs:ignore ?> <?php ev_e( 'back' ); ?></a>
						<a class="ev-link-arrow" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php ev_e( 'to_catalog' ); ?></a>
						<?php if ( $series ) : ?>
							<a class="ev-link-arrow" href="<?php echo esc_url( get_term_link( $series ) ); ?>"><?php ev_e( 'view_series' ); ?> <?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?></a>
						<?php endif; ?>
					</div>
				</div>
			</div>
		</div>
	</article>

	<?php
	if ( $series ) :
		$more = get_posts(
			[
				'post_type'    => 'ev_decor',
				'numberposts'  => 4,
				'post__not_in' => [ $id ],
				'orderby'      => 'rand',
				'tax_query'    => [ [ 'taxonomy' => 'ev_series', 'terms' => $series->term_id ] ], // phpcs:ignore WordPress.DB.SlowDBQuery
			]
		);
		if ( $more ) :
			?>
			<section class="ev-section--tight ev-beige">
				<div class="ev-container">
					<h2 class="ev-h3"><?php ev_e( 'decor_same_series' ); ?></h2>
					<ul class="ev-grid ev-grid--4">
						<?php foreach ( $more as $p ) : ?>
							<?php get_template_part( 'template-parts/decor-card', null, [ 'post' => $p ] ); ?>
						<?php endforeach; ?>
					</ul>
				</div>
			</section>
			<?php
		endif;
	endif;
endwhile;

get_footer();
