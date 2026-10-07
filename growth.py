"""Plot published incident counts at each recorded update, using Git snapshots."""
import json
import math
import subprocess
from updates import JST, REPOSITORY_URL, load_history, parse_timestamp


def load_growth(root):
    history = load_history(root)
    changed = set(subprocess.check_output(
        ['git', '-C', str(root), 'log', '--first-parent', '--format=%H',
         'HEAD', '--', 'data/incidents.json'], text=True).splitlines())
    # Include HEAD so site-only updates extend the final horizontal segment.
    entries = [entry for entry in reversed(history)
               if entry['id'] in changed or entry['id'] == history[0]['id']]
    points = []
    # Stream one snapshot at a time so growing history does not accumulate JSON in memory.
    with subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        for entry in entries:
            process.stdin.write((entry['id'] + ':data/incidents.json\n').encode())
            process.stdin.flush()
            header = process.stdout.readline().split()
            if header[-1] == b'missing':
                continue
            size = int(header[-1])
            records = json.loads(process.stdout.read(size))
            process.stdout.read(1)
            timestamp = parse_timestamp(entry['timestamp']).astimezone(JST)
            # Keep ancestry order even if a committer's clock moves backwards.
            position = max(timestamp.timestamp(), points[-1]['position'] if points else 0)
            count = sum(record['publication_status'] == 'published' for record in records)
            points.append({'commit': entry['id'], 'timestamp': entry['timestamp'],
                           'label': timestamp.strftime('%Y/%m/%d %H:%M:%S'),
                           'position': position, 'count': count,
                           'delta': count - points[-1]['count'] if points else None})
        process.stdin.close()
        if process.wait():
            raise RuntimeError('Could not read incident history from Git.')
    return points


def delta_label(delta):
    if delta is None:
        return '初回の記録'
    return f'前回から {delta:+d}件' if delta else '件数の変更なし'


def render_growth(points, current_count):
    if not points:
        return ''
    first, latest = points[0], points[-1]
    # Round up the scale to four readable intervals; counts always start at zero.
    maximum = max(point['count'] for point in points)
    magnitude = 10 ** math.floor(math.log10(max(maximum / 4, 1)))
    step = max(1, math.ceil(maximum / 4 / magnitude) * magnitude)
    ceiling = step * 4
    span = max(latest['position'] - first['position'], 1)
    for point in points:
        point['x'] = 1000 * (point['position'] - first['position']) / span
        point['y'] = 240 * (1 - point['count'] / ceiling)
    path = f'M {first["x"]:.2f} {first["y"]:.2f}'
    for point in points[1:]:
        path += f' H {point["x"]:.2f} V {point["y"]:.2f}'
    area = path + f' L {latest["x"]:.2f} 240 L 0 240 Z'
    grid = ''.join(f'<line x1="0" x2="1000" y1="{y}" y2="{y}" class="growth-grid"/>'
                   for y in (0, 60, 120, 180, 240))
    markers = ''.join(
        f'<circle class="growth-point" cx="{point["x"]:.2f}" cy="{point["y"]:.2f}" r="3" '
        f'data-label="{point["label"]}" data-count="{point["count"]}" '
        f'data-delta="{delta_label(point["delta"])}" data-commit="{point["commit"]}"/>'
        for point in points)
    ticks = ''.join(f'<span>{step * i}</span>' for i in range(4, -1, -1))
    difference = current_count - latest['count']
    draft_note = (f'<p class="growth-draft-note">現在の収録件数と記録済みの履歴には {difference:+d}件の差分があります。'
                  'グラフには履歴に記録された更新を表示しています。</p>') if difference else ''
    selected = f'{latest["label"]}（日本時間）・{latest["count"]}件・{delta_label(latest["delta"])}'
    return (
        '<section id="growth" class="growth-section" aria-labelledby="growth-heading">'
        '<div class="section-head"><h2 id="growth-heading">収録インシデントの増え方</h2>'
        '<a href="/updates/">更新履歴を見る</a></div>'
        '<div class="growth-summary"><p><strong>' + str(current_count) + '</strong><span>件を収録</span></p>'
        '<span class="growth-frequency">更新ごとの収録件数</span></div>'
        '<p class="section-description">このアプリに収録したインシデントの件数を、更新時刻ごとに表示しています。</p>'
        '<figure class="growth-figure"><div class="growth-plot">'
        '<div class="growth-y-axis" aria-hidden="true">' + ticks + '</div>'
        '<svg id="growth-chart" viewBox="0 0 1000 240" preserveAspectRatio="none" role="img" '
        'aria-labelledby="growth-chart-title growth-chart-desc">'
        '<title id="growth-chart-title">更新時刻ごとの収録インシデント件数</title>'
        f'<desc id="growth-chart-desc">日本時間の{first["label"]}に{first["count"]}件、'
        f'{latest["label"]}に{latest["count"]}件。横軸は更新時刻、縦軸は収録件数。'
        'AI関連報告と検証待ちは含みません。</desc>'
        '<defs><linearGradient id="growth-fill" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#1467c9" stop-opacity=".22"/>'
        '<stop offset="100%" stop-color="#1467c9" stop-opacity=".02"/></linearGradient></defs>'
        + grid + f'<path d="{area}" fill="url(#growth-fill)"/>'
        f'<path d="{path}" class="growth-line"/>' + markers +
        f'<line id="growth-guide" x1="{latest["x"]:.2f}" x2="{latest["x"]:.2f}" y1="0" y2="240"/>'
        f'<circle id="growth-selected" cx="{latest["x"]:.2f}" cy="{latest["y"]:.2f}" r="5"/>'
        '</svg></div><div class="growth-x-axis" aria-hidden="true">'
        f'<span>{first["label"][5:16]}</span><span>更新時刻（日本時間）</span>'
        f'<span>{latest["label"][5:16]}</span></div>'
        '<div id="growth-controls" class="growth-controls" hidden>'
        '<label for="growth-step">更新をたどる</label>'
        f'<input type="range" id="growth-step" min="0" max="{len(points) - 1}" '
        f'value="{len(points) - 1}" aria-valuetext="{selected}"></div>'
        '<figcaption class="growth-caption">'
        f'<output id="growth-readout" for="growth-step"><span>{latest["label"]}（日本時間）</span> · '
        f'<span>{latest["count"]}件</span> · <span>{delta_label(latest["delta"])}</span></output>'
        f'<a id="growth-commit" href="{REPOSITORY_URL}/commit/{latest["commit"]}">この更新を見る</a>'
        '</figcaption></figure>' + draft_note +
        '<p class="growth-note">公開済みの事案のみを集計し、AI関連報告と検証待ちは除外。'
        '続報で同じ事案を重複計上せず、掲載取り下げ時は減少します。'
        '日時は更新を記録した時刻で、事件の発生日・公表日や公開完了時刻とは異なります。</p>'
        '</section>')
