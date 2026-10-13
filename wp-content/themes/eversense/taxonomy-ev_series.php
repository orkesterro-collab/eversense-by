<?php
/**
 * Страница серии: описание и сетка её декоров, ссылка на следующую серию.
 */
defined( 'ABSPATH' ) || exit;
get_header();

$term   = get_queried_object();
$all    = ev_series_list();
$ids    = wp_list_pluck( $all, 'term_id' );
$pos    = array_search( $term->term_id, $ids, true );
$next   = ( false !== $pos && count( $all ) > 1 ) ? $all[ ( $pos + 1 ) % count( $all ) ] : null;
$img    = absint( get_term_meta( $term->term_id, 'ev_image', true ) );
?>
<section class="ev-page-head ev-section--tight">
	<div class="ev-container">
		<?php get_template_part( 'template-parts/breadcrumbs', null, [ 'items' => [ [ ev_t( 'catalog_title' ), ev_catalog_url() ], [ $term->name, null ] ] ] ); ?>
		<div class="ev-series-head">
			<div>
				<p class="ev-eyebrow"><?php ev_e( 'series' ); ?></p>
				<h1 class="ev-display"><?php echo esc_html( $term->name ); ?></h1>
				<?php if ( get_term_meta( $term->term_id, 'ev_lead', true ) ) : ?>
					<p class="ev-lead"><?php echo esc_html( get_term_meta( $term->term_id, 'ev_lead', true ) ); ?></p>
				<?php endif; ?>
				<?php if ( get_term_meta( $term->term_id, 'ev_text', true ) ) : ?>
					<p><?php echo esc_html( get_term_meta( $term->term_id, 'ev_text', true ) ); ?></p>
				<?php endif; ?>
			</div>
			<?php if ( $img ) : ?>
				<div class="ev-series-head__media ev-framed"><?php echo wp_get_attachment_image( $img, 'ev-wide', false, [ 'alt' => '' ] ); ?></div>
			<?php endif; ?>
		</div>
	</div>
</section>

<section class="ev-section--tight">
	<div class="ev-container">
		<?php if ( have_posts() ) : ?>
			<ul class="ev-grid">
				<?php
				while ( have_posts() ) :
					the_post();
					get_template_part( 'template-parts/decor-card', null, [ 'post' => get_post() ] );
				endwhile;
				?>
			</ul>
		<?php else : ?>
			<p><?php ev_e( 'catalog_empty' ); ?></p>
		<?php endif; ?>

		<div class="ev-page-nav">
			<a class="ev-link-arrow ev-link-arrow--back" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php echo ev_icon( 'arrow-l' ); // phpcs:ignore ?> <?php ev_e( 'to_catalog' ); ?></a>
			<?php if ( $next ) : ?>
				<a class="ev-next-series" href="<?php echo esc_url( get_term_link( $next ) ); ?>">
					<span class="ev-eyebrow"><?php ev_e( 'next_series' ); ?></span>
					<span class="ev-h3"><?php echo esc_html( $next->name ); ?> <?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?></span>
				</a>
			<?php endif; ?>
		</div>
	</div>
</section>
<?php
get_footer();
