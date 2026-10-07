import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { projects } from '../site/projects.mjs';

test('build produces 58 standalone project pages and an isolated public release', () => {
  const build = spawnSync(process.execPath, ['scripts/build-site.mjs'], { encoding: 'utf8' });
  assert.equal(build.status, 0, build.stderr);

  // Check homepage content
  const home = readFileSync('dist/index.html', 'utf8');
  assert.match(home, /Complex engineering/);
  assert.match(home, /Beautifully made/);
  assert.match(home, /Engineering, design & marketing/);
  assert.equal((home.match(/class="work-row"/g) || []).length, 9);
  assert.doesNotMatch(home, /tower-title|visual study|heroMetrics/);

  // Leadership checks on home and about
  assert.match(home, /Aryan Panchal/);
  assert.match(home, /Founder & Engineering Lead/);
  assert.match(home, /assets\/aryan-perfect\.jpg/);
  assert.match(home, /Rahul Saranya/);
  assert.match(home, /Partner & Motion Graphics Lead/);
  assert.match(home, /assets\/rahul\.jpg/);
  assert.doesNotMatch(home, /himanshu/i);

  const about = readFileSync('dist/about/index.html', 'utf8');
  assert.match(about, /Aryan Panchal/);
  assert.match(about, /Founder & Engineering Lead/);
  assert.match(about, /assets\/aryan-perfect\.jpg/);
  assert.match(about, /Rahul Saranya/);
  assert.match(about, /Partner & Motion Graphics Lead/);
  assert.match(about, /assets\/rahul\.jpg/);
  assert.doesNotMatch(about, /himanshu/i);

  // Verify all 58 published project pages
  assert.equal(projects.length, 58);
  const images = new Set();
  for (const { slug, caseStudyType } of projects) {
    const html = readFileSync(`dist/case-studies/${slug}/index.html`, 'utf8');
    assert.ok(html.includes(`https://mindmaxing.one/case-studies/${slug}`));
    if (caseStudyType === 'motion') {
      assert.match(html, /motion-video-player/);
      assert.match(html, /motion-theatre-shell/);
      assert.match(html, /Motion craft &amp; visual breakdown|Motion craft & visual breakdown/);
      assert.match(html, /Commission motion or 3D project/);
    } else if (caseStudyType === 'marketing') {
      assert.match(html, /data-demo-start/);
      assert.match(html, /Campaign strategy &amp; rationale|Campaign strategy & rationale/);
      assert.match(html, /Discuss a similar campaign/);
    } else {
      assert.match(html, /data-demo-start/);
      assert.match(html, /How this works/);
      assert.match(html, /Build something like this/);
    }
    assert.doesNotMatch(html, /4\.6X ROAS|238K|380%|guaranteed|flawless|locked 60 FPS/);
    assert.doesNotMatch(html, /himanshu/i);

    const imageMatch = html.match(/property="og:image" content="([^"]+)"/);
    assert.ok(imageMatch, `og:image exists for ${slug}`);
    images.add(imageMatch[1]);
  }
  assert.equal(images.size, 58);

  // Forbidden files check
  for (const forbidden of ['outbound', 'advice', '.git', '.env', 'case-studies-data.js', 'package.json', 'himanshu work', 'himanshu.jpg', 'himanshu-perfect.jpg']) {
    assert.equal(existsSync(`dist/${forbidden}`), false, `forbidden path in dist: ${forbidden}`);
  }

  assert.ok(existsSync('dist/case-studies/index.html'));
  assert.ok(existsSync('dist/about/index.html'));
  assert.ok(existsSync('dist/404.html'));
  assert.ok(existsSync('dist/_redirects'));
  assert.ok(existsSync('dist/assets/aryan-perfect.jpg'));
  assert.ok(existsSync('dist/assets/rahul.jpg'));
  assert.ok(readdirSync('dist/assets').length);
});
