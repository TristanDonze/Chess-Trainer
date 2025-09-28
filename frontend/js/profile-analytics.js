(function () {
    const MOTIF_LABELS = {
        hanging_piece: "Hanging Piece",
        missed_fork: "Missed Fork",
        king_safety: "King Safety",
        endgame_technique: "Endgame Technique",
        major_blunder: "Major Blunder",
        positional_drift: "Positional Drift",
    };

    const RESULT_TAGS = {
        win: "result-win",
        loss: "result-loss",
        draw: "result-draw",
    };

    function render(container, analysis) {
        if (!container) return;

        const phaseRoot = container.querySelector('[data-phase-cards]');
        const trendRoot = container.querySelector('[data-trend-chart]');
        const motifRoot = container.querySelector('[data-motif-list]');
        const gamesRoot = container.querySelector('[data-games-summary]');
        const summaryRoot = container.querySelector('[data-analysis-summary]');
        const message = container.querySelector('[data-analysis-message]');

        [phaseRoot, trendRoot, motifRoot, gamesRoot, summaryRoot].forEach((node) => {
            if (node) node.innerHTML = '';
        });

        if (!analysis || analysis.error) {
            container.classList.add('analysis-empty');
            if (message) {
                message.textContent = analysis?.error || 'Analysis unavailable for this profile.';
                message.removeAttribute('hidden');
            }
            return;
        }

        container.classList.remove('analysis-empty');
        if (message) message.setAttribute('hidden', 'hidden');

        if (summaryRoot) renderSummary(summaryRoot, analysis);
        if (phaseRoot) renderPhaseCards(phaseRoot, analysis.phase_breakdown);
        if (trendRoot) renderTrendChart(trendRoot, analysis.trend || []);
        if (motifRoot) renderMotifs(motifRoot, analysis.motif_counts || []);
        if (gamesRoot) renderGames(gamesRoot, analysis.games || []);
    }

    function renderSummary(root, analysis) {
        const { games_analyzed = 0, severity_totals = {} } = analysis;
        const totalMistakes = analysis.games?.reduce((acc, game) => acc + (game.mistakes?.total || 0), 0) || 0;

        const chips = [
            { label: 'Games', value: games_analyzed },
            { label: 'Mistakes', value: totalMistakes },
        ];
        ['blunder', 'mistake'].forEach((key) => {
            if (severity_totals[key]) {
                chips.push({ label: capitalize(key), value: severity_totals[key] });
            }
        });

        chips.forEach((chip) => {
            const el = document.createElement('span');
            el.className = 'analysis-chip';
            el.innerHTML = `<strong>${chip.value}</strong> ${chip.label}`;
            root.appendChild(el);
        });
    }

    function renderPhaseCards(root, phaseBreakdown) {
        const order = ['opening', 'middlegame', 'endgame'];
        const labels = {
            opening: 'Opening',
            middlegame: 'Middlegame',
            endgame: 'Endgame',
        };

        order.forEach((phase) => {
            const data = phaseBreakdown?.[phase];
            const card = document.createElement('div');
            card.className = 'analysis-card';

            if (!data || !data.moves) {
                card.innerHTML = `
                    <span class="phase-title">${labels[phase]}</span>
                    <span class="phase-empty">No moves analyzed</span>
                `;
            } else {
                const rate = formatPercent(data.rate || 0);
                const mistakes = data.mistakes || 0;
                const moves = data.moves || 0;
                card.innerHTML = `
                    <span class="phase-title">${labels[phase]}</span>
                    <span class="phase-value">${rate}</span>
                    <span class="phase-meta">${mistakes} mistakes over ${moves} moves</span>
                `;
            }
            root.appendChild(card);
        });
    }

    function renderTrendChart(root, trend) {
        if (!trend || !trend.length) {
            const msg = document.createElement('p');
            msg.className = 'analysis-empty-state';
            msg.textContent = 'Not enough games for a trend yet.';
            root.appendChild(msg);
            return;
        }

        const parsed = trend.map((item, idx) => ({
            date: Number.isFinite(item.end_time) ? new Date(item.end_time * 1000) : new Date(Date.now() - (trend.length - idx) * 86400000),
            mistakes: Number(item.mistakes) || 0,
            blunders: Number(item.blunders) || 0,
            label: item.label || `Game ${idx + 1}`,
            result: item.result || 'unknown',
            rate: item.mistake_rate || 0,
            url: item.url || null,
        }));

        const width = Math.max(root.clientWidth || 0, 320);
        const height = 240;
        const margin = { top: 16, right: 24, bottom: 40, left: 44 };

        const svg = d3.create('svg')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('role', 'img')
            .classed('mistake-trend-svg', true);

        const x = d3.scaleTime()
            .domain(d3.extent(parsed, (d) => d.date))
            .range([margin.left, width - margin.right]);

        const y = d3.scaleLinear()
            .domain([0, d3.max(parsed, (d) => d.mistakes) || 1])
            .nice()
            .range([height - margin.bottom, margin.top]);

        const axisColor = getComputedStyle(root).getPropertyValue('--text-secondary-color') || '#94a3b8';

        const xAxis = (g) => g
            .attr('transform', `translate(0, ${height - margin.bottom})`)
            .call(d3.axisBottom(x).ticks(Math.min(parsed.length, 6)).tickFormat(d3.timeFormat('%b %d')))
            .call((g) => g.selectAll('text').style('fill', axisColor).style('font-size', '12px'))
            .call((g) => g.selectAll('path,line').style('stroke', axisColor).style('opacity', 0.6));

        const yAxis = (g) => g
            .attr('transform', `translate(${margin.left}, 0)`)
            .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('d')))
            .call((g) => g.selectAll('text').style('fill', axisColor).style('font-size', '12px'))
            .call((g) => g.selectAll('path,line').style('stroke', axisColor).style('opacity', 0.6));

        svg.append('g').call(xAxis);
        svg.append('g').call(yAxis);

        const line = d3.line()
            .x((d) => x(d.date))
            .y((d) => y(d.mistakes))
            .curve(d3.curveMonotoneX);

        svg.append('path')
            .datum(parsed)
            .attr('class', 'trend-line')
            .attr('fill', 'none')
            .attr('stroke', 'var(--accent-color, #f59e0b)')
            .attr('stroke-width', 3)
            .attr('d', line);

        const points = svg.append('g')
            .attr('class', 'trend-points')
            .selectAll('circle')
            .data(parsed)
            .join('circle')
            .attr('class', (d) => `trend-point ${RESULT_TAGS[d.result] || 'result-unknown'}`)
            .attr('cx', (d) => x(d.date))
            .attr('cy', (d) => y(d.mistakes))
            .attr('r', 5)
            .attr('tabindex', 0)
            .on('keydown', function (event, d) {
                if (event.key === 'Enter' && d.url) {
                    window.open(d.url, '_blank', 'noopener');
                }
            })
            .on('click', (event, d) => {
                if (d.url) {
                    window.open(d.url, '_blank', 'noopener');
                }
            });

        points.append('title')
            .text((d) => `${d.label}\nMistakes: ${d.mistakes}${d.blunders ? ` (blunders: ${d.blunders})` : ''}\nRate: ${formatPercent(d.rate)}`);

        root.appendChild(svg.node());
    }

    function renderMotifs(root, motifs) {
        if (!motifs.length) {
            const msg = document.createElement('p');
            msg.className = 'analysis-empty-state';
            msg.textContent = 'No recurring motifs detected yet.';
            root.appendChild(msg);
            return;
        }

        const top = motifs.slice(0, 6);
        const maxCount = Math.max(...top.map((m) => m.count || 0), 1);

        top.forEach((item) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'motif-item';

            const header = document.createElement('div');
            header.className = 'motif-header';
            const name = document.createElement('span');
            name.className = 'motif-name';
            name.textContent = MOTIF_LABELS[item.motif] || formatLabel(item.motif);
            const count = document.createElement('span');
            count.className = 'motif-count';
            count.textContent = item.count;

            header.appendChild(name);
            header.appendChild(count);

            const bar = document.createElement('div');
            bar.className = 'motif-bar';
            const fill = document.createElement('span');
            fill.style.width = `${Math.max((item.count / maxCount) * 100, 8)}%`;
            bar.appendChild(fill);

            wrapper.appendChild(header);
            wrapper.appendChild(bar);
            root.appendChild(wrapper);
        });
    }

    function renderGames(root, games) {
        if (!games.length) {
            const msg = document.createElement('p');
            msg.className = 'analysis-empty-state';
            msg.textContent = 'No game summaries available yet.';
            root.appendChild(msg);
            return;
        }

        const recent = games.slice(-5).reverse();
        recent.forEach((game) => {
            const item = document.createElement('article');
            item.className = 'analysis-game';

            const top = document.createElement('div');
            top.className = 'analysis-game-top';
            const title = document.createElement('span');
            title.className = 'analysis-game-title';
            title.textContent = `${game.color === 'white' ? 'White' : 'Black'} vs ${game.opponent || 'Opponent'}`;
            top.appendChild(title);

            const badge = document.createElement('span');
            badge.className = `analysis-game-result ${RESULT_TAGS[game.result] || 'result-unknown'}`;
            badge.textContent = capitalize(game.result || 'Unknown');
            top.appendChild(badge);
            item.appendChild(top);

            const stats = document.createElement('div');
            stats.className = 'analysis-game-stats';
            const blunders = game.mistakes?.by_severity?.blunder || 0;
            const mistakes = game.mistakes?.by_severity?.mistake || 0;
            stats.innerHTML = `
                <span><strong>${game.mistakes?.total || 0}</strong> total</span>
                <span>${blunders} blunders</span>
                <span>${mistakes} mistakes</span>
            `;
            item.appendChild(stats);

            const phaseRow = document.createElement('div');
            phaseRow.className = 'analysis-game-phases';
            ['opening', 'middlegame', 'endgame'].forEach((phase) => {
                const breakdown = game.mistakes?.by_phase?.[phase] || 0;
                if (breakdown) {
                    const tag = document.createElement('span');
                    tag.className = 'phase-tag';
                    tag.textContent = `${capitalize(phase)}: ${breakdown}`;
                    phaseRow.appendChild(tag);
                }
            });
            if (phaseRow.childElementCount) {
                item.appendChild(phaseRow);
            }

            if (game.url) {
                const link = document.createElement('a');
                link.className = 'analysis-game-link';
                link.href = game.url;
                link.target = '_blank';
                link.rel = 'noopener';
                link.textContent = 'View game';
                item.appendChild(link);
            }

            root.appendChild(item);
        });
    }

    function formatPercent(value) {
        const numeric = Number(value) || 0;
        return `${Math.round(numeric * 100)}%`;
    }

    function capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function formatLabel(label) {
        return label
            ? label.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())
            : '';
    }

    window.ProfileAnalysis = {
        render,
    };
})();
