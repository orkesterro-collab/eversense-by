<?php defined('ABSPATH') || exit; get_header(); while(have_posts()):the_post(); ?>
<article class="ev-section--tight"><div class="ev-container ev-container--narrow">
<p class="ev-eyebrow"><a href="<?php echo esc_url(get_post_type_archive_link('ev_installer')); ?>">← Все укладчики</a></p>
<h1 class="ev-h1"><?php the_title(); ?></h1>
<p><?php echo esc_html(get_post_meta(get_the_ID(),'ev_city',true)); ?></p>
<div class="ev-prose"><?php the_content(); ?></div>
<?php $tel=get_post_meta(get_the_ID(),'ev_phone',true);if($tel): ?><a class="ev-btn" href="<?php echo esc_attr(ev_tel($tel)); ?>"><?php echo esc_html($tel); ?></a><?php endif; ?>
</div></article><?php endwhile; get_footer(); ?>