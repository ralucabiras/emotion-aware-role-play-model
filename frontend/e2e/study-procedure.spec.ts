import { expect, test } from '@playwright/test'
import { expectAccessible, installApiMock } from './support'

test('enrolled participant follows all three guided tasks at intermediate difficulty', async ({page})=>{
  await installApiMock(page,{enrolled:true})
  await page.goto('/app')
  const checklist=page.getByRole('region',{name:'Your study checklist'})
  // A named section is exposed as a region by browsers.
  await expect(checklist).toContainText('0 of 3 tasks complete')
  await checklist.getByRole('button',{name:'Next task: Workload conversation'}).click()
  for(const [index,id,title] of [[0,'workload','Workload conversation'],[1,'boundary','Boundary conversation'],[2,'relationship','Relationship conversation']] as const){
    await expect(page.getByText('Required study task - intermediate difficulty.')).toBeVisible()
    await expect(page.getByRole('radio')).toHaveCount(0)
    await expect(page.getByRole('button',{name:'+ Create your own scenario'})).toHaveCount(0)
    const start=page.waitForRequest(request=>request.url().endsWith('/session-1/roleplay'))
    await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
    expect((await start).postDataJSON()).toMatchObject({scenario_id:id,difficulty:'intermediate'})
    await page.getByRole('button',{name:'Finish & review'}).click()
    await expect(checklist).toContainText('Answer or skip the post-ratings below')
    await page.getByLabel('Confidence now').selectOption('5')
    await page.getByLabel('Scenario realism').selectOption('6')
    await page.getByLabel('Feedback usefulness').selectOption('7')
    await page.getByRole('button',{name:'Save research ratings'}).click()
    await expect(checklist).toContainText(`${index+1} of 3 tasks complete`)
    await expect(checklist.locator('li').nth(index)).toContainText(title)
    if(index<2){
      const nextTitle=index===0?'Boundary conversation':'Relationship conversation'
      await checklist.getByRole('button',{name:`Next task: ${nextTitle}`}).click()
    }
  }
  await expect(checklist).toContainText('you have reached the end of the study tasks')
  await expect(checklist.getByRole('button',{name:/Next task/})).toHaveCount(0)
  await page.goto('/app')
  await expect(checklist).toContainText('3 of 3 tasks complete')
  await expectAccessible(page)
})

test('a skipped post-questionnaire advances the guide without claiming completion',async({page})=>{
  await installApiMock(page,{enrolled:true})
  await page.goto('/practice?mode=roleplay&study=workload')
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  await page.getByRole('button',{name:'Finish & review'}).click()
  await page.getByRole('button',{name:'Skip post-ratings'}).click()
  const checklist=page.getByRole('region',{name:'Your study checklist'})
  await expect(checklist).toContainText('0 of 3 tasks complete')
  await expect(checklist.locator('li').first()).toContainText('Attempt recorded - incomplete')
  await expect(checklist.getByRole('button',{name:'Next task: Boundary conversation'})).toBeVisible()
})

test('ordinary practice keeps scenario and difficulty choices',async({page})=>{
  await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await expect(page.getByRole('region',{name:'Your study checklist'})).toHaveCount(0)
  await expect(page.getByRole('radio',{name:/beginner/})).toBeChecked()
  await expect(page.getByRole('button',{name:'+ Create your own scenario'})).toBeVisible()
})
