// Local artifact checks only. No provider/model calls, no external page visits.
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm');
const base='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1123-915-0_26.1123.915.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
const root=__dirname;
const html=fs.readFileSync(path.join(root,'dashboard.html'),'utf8');
const js=html.match(/<script>([\s\S]*)<\/script>/)[1];
new vm.Script(js,{filename:'dashboard-inline.js'});
const report=fs.readFileSync(path.join(root,'报告.md'),'utf8');
const links=[...report.matchAll(/\]\(([^)]+)\)/g)].map(m=>m[1]);
for(const link of links){if(!/^https?:/.test(link)&&!fs.existsSync(path.join(root,link)))throw new Error('Missing report link: '+link);}
const summaries=JSON.parse(fs.readFileSync(path.join(root,'harness-summary.json'),'utf8'));
const totals=JSON.parse(fs.readFileSync(path.join(root,'totals.json'),'utf8'));
if(summaries.length!==6 || summaries.some(s=>s.trials!==59) || totals.strict_passed!==134 || totals.requests_unknown!==0)throw new Error('Summary check');
const {chromium}=require(require.resolve('playwright',{paths:[base]}));
(async()=>{
 const executablePath=['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Google/Chrome/Application/chrome.exe'].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1120}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.route(/^https?:/,r=>r.abort());
  await page.goto('file:///'+path.join(root,'dashboard.html').replaceAll('\\','/'));
  await page.waitForSelector('#rows tr');
  const count=await page.locator('#rows tr').count();
  if(count!==354)throw new Error('Expected354, got '+count);
  await page.locator('#h').selectOption('latte-planning-adapted');
  if(await page.locator('#rows tr').count()!==59)throw new Error('Harness filter');
  await page.locator('#task').fill('C031');
  if(await page.locator('#rows tr').count()!==1)throw new Error('Task filter');
  const evidence=await page.locator('#rows tr').innerText();
  if(!evidence.includes('7/9')||!evidence.includes('0.846154'))throw new Error('C031 evidence');
  await page.locator('#task').fill('');await page.locator('#h').selectOption('');
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(root,'dashboard-preview.png'),fullPage:false});
  if(errors.length)throw new Error(errors.join('\n'));
  const receipt={html_script_syntax:'passed',relative_report_links:links.length,summary_rows:await page.locator('#summary tr').count(),detail_rows:count,harness_filter:'passed',task_filter:'passed',latte_C031_api_reward:'7/9;0.846154',external_http_requests:'blocked',page_errors:errors,canvas_typecheck:'not available from this command runner; exports/props checked against SDK declarations'};
  fs.writeFileSync(path.join(root,'artifact-verification.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
