"""Manual fixed validation labels; no inference creates these labels."""
import hashlib,json
from bench import ROOT
sample=json.loads((ROOT/'data/sample.json').read_text())
# Source index, entailed claim, explicitly incompatible claim, unmentioned claim.
specs=[
(3,'{S} has known these friends for four years.','{S} has known these friends for only one year.','{S} lives in a three-bedroom house.'),
(5,'{S} passed adoption interviews last Friday.','{S} failed those adoption interviews last Friday.','{S} has already adopted two children.'),
(18,'{S} lost their job.','{S} has never lost a job.','{S} owns the studio building.'),
(51,'{S} felt satisfied by the movie screening.','{S} felt no satisfaction at all from that screening.','{S} directed the movie.'),
(89,'{e0} is a {e2} mix.','{e0} is not a {e2} mix.','{S} adopted {e0} yesterday.'),
(150,'{S} currently likes indie rock.','{S} currently dislikes indie rock.','{S} lives in the city where the band formed.'),
(153,'{S} used to be a staunch atheist.','{S} has never been an atheist.','{S} now belongs to a specific religion.'),
(161,"{S}'s asylum application was approved.","{S}'s asylum application was rejected and never approved.",'{S} obtained citizenship last week.'),
(172,"{S} volunteered at a fundraising dinner on Valentine's Day.","{S} did not volunteer at that dinner on Valentine's Day.",'{S} won the raffle prize.'),
(180,'{S} downloaded the {e4} app.','{S} has not downloaded the {e4} app.','{S} bought travel insurance for the trip.'),
(201,'{S} enjoys the flexibility of working from home.','{S} dislikes the flexibility of working from home.','{S} works from home and earns $100,000 a year.'),
(214,'{S} bought the phone for $800.','{S} bought the phone for $700 rather than $800.','{S} bought the phone for $800 and paid in cash.'),
(237,'{S} achieved a quarter-mile personal best of 12.8 seconds.','{S} achieved a quarter-mile personal best of 15 seconds instead of 12.8.','{S} achieved that personal best in June 2023.'),
(248,'{S} needs 125 stars to reach the specified level.','{S} needs 400 stars rather than 125 to reach that level.','{S} earned those stars by buying coffee.'),
(251,'{S} has lost 10 pounds since starting consistent gym visits.','{S} gained 10 pounds instead of losing weight over that period.','{S} lost 10 pounds in one week.'),
(254,'{S} was pre-approved for $350,000.','{S} was pre-approved for only $300,000.','{S} was pre-approved at a five percent interest rate.'),
(258,'{S} eventually aims to reach level 150.','{S} has no intention of ever reaching level 150.','{S} plays on a premium gaming console.'),
(272,'{S} usually works 40 hours a week.','{S} usually works only 20 hours a week.','{S} works 40 hours a week as a nurse.'),
(291,'{S} attends weightlifting on Saturdays at 10 am.','{S} attends that Saturday weightlifting class at 10 pm instead of 10 am.','{S} attends the class with their brother.'),
(295,'{S} now has 200 loyalty points.','{S} now has only 100 loyalty points.','{S} has 200 loyalty points that expire tomorrow.'),
]
import re
rows=[]
for index,supported,contradicted,unknown in specs:
 r=sample[index];es=list(dict.fromkeys(re.findall(r'ENTITY_\d+',r['text'])));m={'S':r['speaker'],**{f'e{i}':e for i,e in enumerate(es)}}
 source=r['speaker']+' says: '+r['text']
 for label,claim in [('supported',supported),('contradicted',contradicted),('unknown',unknown)]:
  premise=source;kind='source'
  if label=='unknown'and index>=201:
   # Explicitly incomplete writer output. The original turn is absent.
   premise=supported.format(**m);kind='coverage'
  rows.append({'id':f'{index}-{label}','kind':kind,'source_index':index,'premise':premise,'hypothesis':claim.format(**m),'expected':label,'review':'Direct manual source inspection by implementing agent; no independent human adjudicator.'})
(ROOT/'data/judge-validation.json').write_text(json.dumps(rows,indent=2)+'\n')
(ROOT/'judge-protocol-lock.json').write_text(json.dumps({'prompt_sha256':hashlib.sha256((ROOT/'judge_prompt.txt').read_bytes()).hexdigest(),'validation_sha256':hashlib.sha256((ROOT/'data/judge-validation.json').read_bytes()).hexdigest(),'minimum_agreement':54,'N':60,'separate_source_and_coverage':True},indent=2)+'\n')
