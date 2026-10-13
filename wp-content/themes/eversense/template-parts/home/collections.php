<?php
defined( 'ABSPATH' ) || exit;
$series = ev_series_list();
?>
<section class="ev-collections ev-section">
	<div class="ev-container">
		<div class="ev-section-head" data-reveal>
			<h2 class="ev-h2"><?php ev_e( 'collections_title' ); ?></h2>
			<p class="ev-lead"><?php ev_e( 'collections_text' ); ?></p>
		</div>

		<div class="ev-series-list">
			<?php foreach ( $series as $i => $term ) : ?>
				<?php get_template_part( 'template-parts/series-card', null, [ 'term' => $term, 'index' => $i ] ); ?>
			<?php endforeach; ?>
		</div>
	</div>
</section>
