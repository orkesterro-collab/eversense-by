<?php
/**
 * Каталог: все серии, в каждой — сетка декоров.
 */
defined( 'ABSPATH' ) || exit;
get_header();

$series = ev_series_list();
$byterm = [];
if ( have_posts() ) {
	while ( have_posts() ) {
		the_post();
		$s                   = ev_decor_series();
		$byterm[ $s ? $s->term_id : 0 ][] = get_post();
	}
}
?>
<section class="ev-page-head ev-section--tight">
	<div class="ev-container">
		<?php get_template_part( 'template-parts/breadcrumbs', null, [ 'items' => [ [ ev_t( 'catalog_title' ), null ] ] ] ); ?>
		<h1 class="ev-display"><?php ev_e( 'catalog_title' ); ?></h1>
		<p class="ev-lead"><?php ev_e( 'catalog_lead' ); ?></p>
		<?php if ( $series ) : ?>
			<nav class="ev-chips" aria-label="<?php echo esc_attr( ev_t( 'series' ) ); ?>">
				<span class="ev-chip is-active"><?php ev_e( 'catalog_all' ); ?></span>
				<?php foreach ( $series as $t ) : ?>
					<a class="ev-chip" href="#series-<?php echo esc_attr( $t->term_id ); ?>"><?php echo esc_html( $t->name ); ?></a>
				<?php endforeach; ?>
			</nav>
		<?php endif; ?>
	</div>
</section>

<?php foreach ( $series as $t ) : ?>
	<?php
	if ( empty( $byterm[ $t->term_id ] ) ) {
		continue;
	}
	?>
	<section class="ev-catalog-group ev-section--tight" id="series-<?php echo esc_attr( $t->term_id ); ?>">
		<div class="ev-container">
			<header class="ev-catalog-group__head">
				<div>
					<p class="ev-eyebrow"><?php ev_e( 'series' ); ?></p>
					<h2 class="ev-h2"><a href="<?php echo esc_url( get_term_link( $t ) ); ?>"><?php echo esc_html( $t->name ); ?></a></h2>
					<?php if ( get_term_meta( $t->term_id, 'ev_lead', true ) ) : ?>
						<p><?php echo esc_html( get_term_meta( $t->term_id, 'ev_lead', true ) ); ?></p>
					<?php endif; ?>
				</div>
				<a class="ev-link-arrow" href="<?php echo esc_url( get_term_link( $t ) ); ?>"><?php ev_e( 'view_series' ); ?> <?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?></a>
			</header>
			<ul class="ev-grid">
				<?php foreach ( $byterm[ $t->term_id ] as $p ) : ?>
					<?php get_template_part( 'template-parts/decor-card', null, [ 'post' => $p ] ); ?>
				<?php endforeach; ?>
			</ul>
		</div>
	</section>
<?php endforeach; ?>

<?php if ( ! empty( $byterm[0] ) ) : ?>
	<section class="ev-catalog-group ev-section--tight">
		<div class="ev-container">
			<ul class="ev-grid">
				<?php foreach ( $byterm[0] as $p ) : ?>
					<?php get_template_part( 'template-parts/decor-card', null, [ 'post' => $p ] ); ?>
				<?php endforeach; ?>
			</ul>
		</div>
	</section>
<?php endif; ?>

<?php
get_footer();
