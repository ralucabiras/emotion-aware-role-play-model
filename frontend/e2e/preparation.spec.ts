import { expect, test, type Page } from '@playwright/test'
import type { ActionCard, Scenario, ScenarioDraft } from '../src/types/api'
import { expectAccessible, installApiMock } from './support'

const draft:ScenarioDraft={title:'Talk with my housemate',character:'my housemate',situation:'I have been doing dishes every evening this week.',user_objective:'Share the dishes on weekdays.',opening_line:'You wanted to talk. What would you like to change?',skills:['clear request','specific detail'],preparation:{difficult_part:'I worry about blame.',likely_objection:'I also have a busy week. What do you suggest?',flow:'request',source:'template-v1'}}

async function preparationFixture(page:Page,offline=false){
  const mock=await installApiMock(page)
  let saved:Scenario|null=null,failSave=false
  const writes:ScenarioDraft[]=[]
  await page.route('**/api/roleplay/preparation',route=>route.fulfill({status:offline?503:200,contentType:'application/json',body:JSON.stringify(offline?{detail:'Unavailable'}:draft)}))
  await page.route('**/api/roleplay/scenarios**',async route=>{
    const request=route.request()
    if(request.method()==='GET')return saved?route.fulfill({contentType:'application/json',body:JSON.stringify([saved])}):route.fallback()
    if(['POST','PUT'].includes(request.method())){
      if(failSave)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Brief could not be saved. Try again.'})})
      const value=request.postDataJSON() as ScenarioDraft;writes.push(value)
      const result={...value,id:'custom_prepared',expected_skills:value.skills}
      saved=result;mock.customScenario=result
      return route.fulfill({contentType:'application/json',body:JSON.stringify(result)})
    }
    return route.fallback()
  })
  return {writes,setFail:(value:boolean)=>{failSave=value}}
}

async function answers(page:Page){
  await page.goto('/practice?mode=roleplay');await page.getByRole('button',{name:'Prepare a real conversation',exact:true}).click()
  await page.getByLabel('Who will you speak with?').fill('my housemate')
  await page.getByLabel('What happened?').fill(draft.situation)
  await page.getByLabel('What would you like to happen?').fill(draft.user_objective)
  await page.getByLabel('What feels difficult about it?').fill('I worry about blame.')
}

test('reviews and edits a brief before starting, then edits it after reload',async({page})=>{
  const state=await preparationFixture(page)
  await answers(page);await page.getByRole('button',{name:'Prepare my brief',exact:true}).click()
  await expect(page.getByRole('button',{name:'Skip pre-ratings and begin'})).toHaveCount(0)
  expect(state.writes).toEqual([])
  await page.getByLabel('A possible objection').fill('How would Monday work for you?')
  await page.getByLabel('Their opening line').fill('What would help us share the work?')
  await expectAccessible(page)
  await page.getByRole('button',{name:'Confirm and save brief'}).focus();await page.keyboard.press('Enter')
  expect(state.writes[0].preparation?.likely_objection).toBe('How would Monday work for you?')
  await page.reload()
  await page.getByRole('button',{name:'Edit Talk with my housemate',exact:true}).click()
  await expect(page.getByLabel('A possible objection')).toHaveValue('How would Monday work for you?')
  await page.getByLabel('Brief title').fill('Sharing chores')
  await page.getByRole('button',{name:'Save brief changes'}).click()
  await expect(page.getByText('respond to “How would Monday work for you?”',{exact:false})).toBeVisible()
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  await expect(page.getByText('What would help us share the work?',{exact:true})).toBeVisible()
  expect(state.writes).toHaveLength(2)
})

test('preparation outage and save failure preserve answers and reviewed edits',async({page})=>{
  const state=await preparationFixture(page,true)
  await answers(page);await page.getByRole('button',{name:'Prepare my brief',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('Your answers are kept')
  await expect(page.getByLabel('Who will you speak with?')).toHaveValue('my housemate')
  await page.getByRole('button',{name:'Use offline template'}).click()
  await page.getByLabel('What to practise').selectOption('boundary')
  await page.getByLabel('A possible objection').fill('Could you do it just this once?')
  state.setFail(true);await page.getByRole('button',{name:'Confirm and save brief'}).click()
  await expect(page.getByRole('alert')).toHaveText('Brief could not be saved. Try again.')
  await expect(page.getByLabel('A possible objection')).toHaveValue('Could you do it just this once?')
  state.setFail(false);await page.getByRole('button',{name:'Confirm and save brief'}).click()
  expect(state.writes[0].skills).toEqual(['boundary maintenance','non-blaming language'])
})

test('an older custom scenario opens for editing without preparation metadata',async({page})=>{
  await installApiMock(page)
  const legacy={id:'custom_old',title:'Old conversation',character:'team lead',situation:'Discuss an uneven split of recurring work.',user_objective:'Ask to share the recurring work.',opening_line:'What did you want to discuss?',expected_skills:['clear request']}
  let changed:ScenarioDraft|null=null
  await page.route('**/api/roleplay/scenarios',route=>route.fulfill({contentType:'application/json',body:JSON.stringify([legacy])}))
  await page.route('**/api/roleplay/scenarios/custom_old',route=>{changed=route.request().postDataJSON();return route.fulfill({contentType:'application/json',body:JSON.stringify({...legacy,...changed})})})
  await page.goto('/practice?mode=roleplay');await page.getByRole('button',{name:'Edit Old conversation',exact:true}).click()
  await expect(page.getByLabel('Brief title')).toHaveValue('Old conversation')
  await page.getByLabel('Desired outcome').fill('Ask to rotate the Monday meeting notes.')
  await page.getByRole('button',{name:'Save brief changes'}).click()
  await expect(page.getByText('Ask to rotate the Monday meeting notes.',{exact:true})).toBeVisible()
  expect(changed).toMatchObject({user_objective:'Ask to rotate the Monday meeting notes.',skills:['clear request']})
})

async function cardFixture(page:Page){
  const mock=await installApiMock(page,{existingSession:true});mock.roleplay={scenario_id:'workload',status:'completed',difficulty_level:'intermediate',turn:1,success_progress:1}
  let card:ActionCard={opening_sentence:'Could we talk about my workload?',main_request:'Ask for clearer priorities.',boundary_or_fallback:'I can pause and suggest another time.',reminder:'One request at a time.',source:'template-v1',source_turn_ids:['turn-old'],updated_at:'2026-09-28T10:00:00Z'},saved=false,version=4,fail=false,failLoad=false
  await page.addInitScript(()=>{Object.defineProperty(navigator,'clipboard',{value:{writeText:async(text:string)=>{sessionStorage.setItem('copied-card',text)}}})})
  await page.route('**/api/sessions/session-1/action-card',route=>{
    if(failLoad)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Card temporarily unavailable'})})
    if(route.request().method()==='PUT'){
      const data=route.request().postDataJSON()
      if(fail||data.expected_version!==version){version++;return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'This session changed. Refresh the saved version before saving your card.'})})}
      card={...card,opening_sentence:data.opening_sentence,main_request:data.main_request,boundary_or_fallback:data.boundary_or_fallback,reminder:data.reminder,source:'user-edited'};saved=true;version++
    }
    return route.fulfill({contentType:'application/json',body:JSON.stringify({card,saved,version})})
  })
  return {setFail:(value:boolean)=>{fail=value},setLoadFail:(value:boolean)=>{failLoad=value},card:()=>card}
}

test('action card saves, reloads, copies and downloads current wording',async({page})=>{
  const state=await cardFixture(page)
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Action card',exact:true}).click()
  await page.getByLabel('Main request',{exact:true}).fill('Could we move the internal report to Monday?')
  await page.getByRole('button',{name:'Save action card',exact:true}).click();await expect(page.getByRole('status')).toHaveText('Action card saved.')
  expect(state.card().main_request).toBe('Could we move the internal report to Monday?')
  await page.reload();await page.getByRole('button',{name:'Action card',exact:true}).click()
  await expect(page.getByLabel('Main request',{exact:true})).toHaveValue('Could we move the internal report to Monday?')
  await page.getByRole('button',{name:'Copy text',exact:true}).click()
  expect(await page.evaluate(()=>sessionStorage.getItem('copied-card'))).toContain('not an agreed commitment')
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download text',exact:true}).click()
  const file=await download;expect(file.suggestedFilename()).toBe('conversation-action-card.txt')
  const stream=await file.createReadStream();let text='';for await(const chunk of stream!)text+=chunk.toString()
  expect(text).toContain('Could we move the internal report to Monday?')
  await expectAccessible(page)
})

test('action card recovers from load and stale-save failures without losing edits',async({page})=>{
  const state=await cardFixture(page);state.setLoadFail(true)
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Action card',exact:true}).click()
  await expect(page.getByRole('alert')).toHaveText('Card temporarily unavailable')
  state.setLoadFail(false);await page.getByRole('button',{name:'Retry loading action card'}).click()
  await page.getByLabel('One reminder',{exact:true}).fill('My own reminder.')
  state.setFail(true);await page.getByRole('button',{name:'Save action card',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('This session changed')
  state.setFail(false);await page.getByRole('button',{name:'Refresh saved version and keep my draft'}).click()
  await expect(page.getByLabel('One reminder',{exact:true})).toHaveValue('My own reminder.')
  await page.getByRole('button',{name:'Save action card',exact:true}).click();await expect(page.getByRole('status')).toHaveText('Action card saved.')
})
