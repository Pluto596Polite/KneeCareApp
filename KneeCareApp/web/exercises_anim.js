/* Self-contained animated SVG illustrations for each exercise.
   No external assets, no network, no licensing. Colours inherit from the page
   via the CSS custom properties --fig (figure) and --acc (active/moving part). */
(function () {
  const W = 260, H = 170, BED = 128;
  const wrap = (inner, caption) =>
    `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${caption}">
       <style>
         .fig{fill:none;stroke:var(--fig,#334155);stroke-width:7;stroke-linecap:round;stroke-linejoin:round}
         .acc{fill:none;stroke:var(--acc,#4f46e5);stroke-width:8;stroke-linecap:round;stroke-linejoin:round}
         .joint{fill:var(--fig,#334155)}
         .skin{fill:var(--surface2,#eef2f7)}
         .bed{fill:var(--surface2,#e9eef5)}
         .arrow{fill:var(--acc,#4f46e5)}
         .muscle{fill:var(--acc,#4f46e5);opacity:.18}
       </style>
       <rect class="bed" x="8" y="${BED}" width="${W-16}" height="10" rx="5"/>
       ${inner}
     </svg>`;

  // reclined upper body (head + torso) facing right, hip at (hx,hy)
  const torso = (hx, hy) =>
    `<line class="fig" x1="${hx}" y1="${hy}" x2="${hx-78}" y2="${hy-14}"/>
     <circle class="skin" cx="${hx-92}" cy="${hy-18}" r="13" stroke="var(--fig,#334155)" stroke-width="3"/>
     <circle class="joint" cx="${hx}" cy="${hy}" r="6"/>`;

  const A = {};

  // 1. Ankle pumps – foot pivots up/down at the ankle
  A.ankle_pumps = wrap(`
    <line class="fig" x1="70" y1="96" x2="168" y2="96"/>
    <circle class="joint" cx="168" cy="96" r="6"/>
    <g transform="translate(168,96)">
      <line class="acc" x1="0" y1="0" x2="34" y2="0">
        <animateTransform attributeName="transform" type="rotate"
          values="-38;28;-38" keyTimes="0;0.5;1" dur="1.5s" repeatCount="indefinite"/>
      </line>
    </g>
    <path class="arrow" d="M214 60 l8 0 l-4 -9 z"/><path class="arrow" d="M214 92 l8 0 l-4 9 z"/>
  `, "Ankle pumps");

  // 2. Ankle rotations – foot traces a circle
  A.ankle_rotations = wrap(`
    <line class="fig" x1="70" y1="96" x2="168" y2="96"/>
    <circle class="joint" cx="168" cy="96" r="6"/>
    <g transform="translate(168,96)">
      <line class="acc" x1="0" y1="0" x2="32" y2="0">
        <animateTransform attributeName="transform" type="rotate"
          values="0;360" dur="2.4s" repeatCount="indefinite"/>
      </line>
    </g>
    <circle cx="190" cy="96" r="26" fill="none" stroke="var(--acc,#4f46e5)" stroke-width="2" stroke-dasharray="3 5" opacity="0.5"/>
  `, "Ankle rotations");

  // 3. Deep breaths – chest/abdomen expands
  A.breaths = wrap(`
    <line class="fig" x1="60" y1="100" x2="150" y2="100"/>
    <circle class="skin" cx="46" cy="96" r="13" stroke="var(--fig,#334155)" stroke-width="3"/>
    <line class="fig" x1="150" y1="100" x2="196" y2="100"/>
    <ellipse class="muscle" cx="120" cy="92" rx="26" ry="16">
      <animate attributeName="ry" values="10;22;10" dur="2.6s" repeatCount="indefinite"/>
      <animate attributeName="cy" values="96;86;96" dur="2.6s" repeatCount="indefinite"/>
    </ellipse>
    <path class="arrow" d="M120 56 l7 0 l-3.5 -9 z" opacity="0.9"/>
  `, "Deep breaths");

  // helper: jointed leg lying on bed, hip at hx,hy. thighVals/shinVals are rotate keyframes
  const legLying = (hx, hy, thighVals, shinVals, dur, extra = "") =>
    `${torso(hx, hy)}
     <g transform="translate(${hx},${hy})">
       <g><animateTransform attributeName="transform" type="rotate" values="${thighVals}" keyTimes="0;0.5;1" dur="${dur}" repeatCount="indefinite"/>
         <line class="acc" x1="0" y1="0" x2="58" y2="0"/>
         <g transform="translate(58,0)">
           <circle class="joint" cx="0" cy="0" r="5"/>
           <g><animateTransform attributeName="transform" type="rotate" values="${shinVals}" keyTimes="0;0.5;1" dur="${dur}" repeatCount="indefinite"/>
             <line class="acc" x1="0" y1="0" x2="52" y2="0"/>
             <line class="fig" x1="52" y1="0" x2="66" y2="6"/>
           </g>
         </g>
       </g>
     </g>${extra}`;

  // 4. Quadriceps sets – press the back of the knee down, thigh tightens (small motion + muscle pulse)
  A.quad_sets = wrap(`
    ${torso(150,96)}
    <line class="acc" x1="150" y1="96" x2="208" y2="96"/>
    <circle class="joint" cx="208" cy="96" r="5"/>
    <line class="acc" x1="208" y1="96" x2="244" y2="100"/>
    <ellipse class="muscle" cx="178" cy="92" rx="22" ry="9">
      <animate attributeName="ry" values="6;11;6" dur="1.6s" repeatCount="indefinite"/>
    </ellipse>
    <path class="arrow" d="M208 112 l-5 0 l2.5 8 z"/>
  `, "Quadriceps sets");

  // 5. Gluteal sets – squeeze the buttocks
  A.glute_sets = wrap(`
    ${torso(168,96)}
    <line class="acc" x1="168" y1="96" x2="226" y2="98"/>
    <circle class="muscle" cx="158" cy="92" r="16">
      <animate attributeName="r" values="12;18;12" dur="1.6s" repeatCount="indefinite"/>
    </circle>
    <path class="arrow" d="M138 92 l-9 -4 l0 8 z"/><path class="arrow" d="M178 92 l9 -4 l0 8 z"/>
  `, "Gluteal sets");

  // 6. Heel slides – bend the knee, sliding the heel toward the hip, then straighten
  A.heel_slides = wrap(
    legLying(150, 96, "0;-46;0", "0;-92;0", "2.4s"),
    "Heel slides");

  // 7. Straight leg raises – keep knee straight, lift the whole leg
  A.slr = wrap(
    legLying(150, 96, "0;-34;0", "0;0;0", "2.4s",
      `<path class="arrow" d="M250 70 l0 -9 l-7 4.5 z" opacity="0.8"/>`),
    "Straight leg raises");

  // 8. Short-arc quads – towel under knee, straighten the lower leg
  A.short_arc = wrap(
    `${torso(150,96)}
     <line class="acc" x1="150" y1="96" x2="196" y2="84"/>
     <ellipse class="bed" cx="196" cy="92" rx="13" ry="9"/>
     <circle class="joint" cx="196" cy="84" r="5"/>
     <g transform="translate(196,84)">
       <g><animateTransform attributeName="transform" type="rotate" values="48;6;48" keyTimes="0;0.5;1" dur="2s" repeatCount="indefinite"/>
         <line class="acc" x1="0" y1="0" x2="50" y2="0"/>
         <line class="fig" x1="50" y1="0" x2="64" y2="6"/>
       </g>
     </g>`,
    "Short-arc quads");

  // 9. Knee extension stretch – heel propped, knee sags down to straighten
  A.knee_ext = wrap(
    `${torso(110,92)}
     <line class="fig" x1="110" y1="92" x2="162" y2="92"/>
     <circle class="joint" cx="162" cy="92" r="5"/>
     <g transform="translate(162,92)">
       <g><animateTransform attributeName="transform" type="rotate" values="-6;14;-6" keyTimes="0;0.5;1" dur="2.6s" repeatCount="indefinite"/>
         <line class="acc" x1="0" y1="0" x2="58" y2="0"/>
       </g>
     </g>
     <rect class="bed" x="214" y="96" width="22" height="26" rx="4"/>
     <path class="arrow" d="M196 70 l5 0 l-2.5 -8 z"/>`,
    "Knee extension stretch");

  // 10. Seated knee bends – sitting, swing the lower leg back to bend the knee
  A.seated_bends = wrap(
    `<rect class="bed" x="40" y="70" width="20" height="58" rx="4"/>
     <rect class="bed" x="40" y="66" width="58" height="8" rx="4"/>
     <line class="fig" x1="64" y1="46" x2="64" y2="74"/>
     <circle class="skin" cx="64" cy="38" r="12" stroke="var(--fig,#334155)" stroke-width="3"/>
     <line class="acc" x1="64" y1="74" x2="120" y2="74"/>
     <circle class="joint" cx="120" cy="74" r="5"/>
     <g transform="translate(120,74)">
       <g><animateTransform attributeName="transform" type="rotate" values="90;150;90" keyTimes="0;0.5;1" dur="2.2s" repeatCount="indefinite"/>
         <line class="acc" x1="0" y1="0" x2="50" y2="0"/>
         <line class="fig" x1="50" y1="0" x2="58" y2="-8"/>
       </g>
     </g>`,
    "Seated knee bends");

  window.EX_ANIM = A;
  window.EX_ANIM_FALLBACK = wrap(
    `<line class="fig" x1="70" y1="96" x2="150" y2="96"/>
     <circle class="joint" cx="150" cy="96" r="5"/>
     <g transform="translate(150,96)"><line class="acc" x1="0" y1="0" x2="46" y2="0">
       <animateTransform attributeName="transform" type="rotate" values="0;-40;0" keyTimes="0;0.5;1" dur="2s" repeatCount="indefinite"/>
     </line></g>`, "Exercise");
})();
