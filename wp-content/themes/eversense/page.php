<?php
/** Обычная страница (политика и т.п.). */
defined( 'ABSPATH' ) || exit;
get_header();
while ( have_posts() ) :
	the_post();
	?>
	<article class="ev-section--tight">
		<div class="ev-container ev-container--narrow">
			<?php get_template_part( 'template-parts/breadcrumbs', null, [ 'items' => [ [ get_the_title(), null ] ] ] ); ?>
			<h1 class="ev-h1"><?php the_title(); ?></h1>
			<div class="ev-prose"><?php the_content(); ?></div>
		</div>
	</article>
	<?php
endwhile;
get_footer();
