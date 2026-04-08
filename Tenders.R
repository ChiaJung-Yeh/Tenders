library(httr)
library(rvest)
library(dplyr)

all_keyword=c("割草","油漆","驅趕","移除","修繕","粉刷","維護","修補")
AMOUNT_THRE=1000000


date_convert=function(x){
  temp=as.numeric(unlist(strsplit(x, "/")))
  return(as.Date(paste0(temp[1]+1911, "-", temp[2], "-", temp[3])))
}

today=as.Date(Sys.time(), tz="Asia/Taipei")

all_tender=data.frame()
for(i in c(1:length(all_keyword))){
  html_content=read_html(paste0("https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic?pageSize=10000&firstSearch=true&searchType=basic&isBinding=N&isLogIn=N&level_1=on&orgName=&orgId=&tenderName=", URLencode(all_keyword[i]), "&tenderId=&tenderType=TENDER_DECLARATION&tenderWay=TENDER_WAY_ALL_DECLARATION&dateType=isDate&tenderStartDate=", gsub("-", "%2F", today-30), "&tenderEndDate=", gsub("-", "%2F", today)))
  
  temp=gsub("\r|\n|\t", "", html_text(html_nodes(html_content, "#tpam td:nth-child(3)")))

  temp=data.frame(OfficeName=gsub("\r|\n|\t", "", html_text(html_nodes(html_content, "#tpam td:nth-child(2)"))),
                  CaseID=gsub(" ", "", substr(temp, 1, regexpr("var hw", temp)-1)),
                  CaseName=gsub('\\("|\\")', "", substr(temp, regexpr("pageCode2Img", temp)+nchar("pageCode2Img"), regexpr("\\;\\$\\(", temp)-1)),
                  DisseminationDate=as.Date(unlist(lapply(gsub("\r|\n|\t", "", html_text(html_nodes(html_content, "#tpam td:nth-child(7)"))), date_convert))),
                  DeadlineDate=as.Date(unlist(lapply(gsub("\r|\n|\t", "", html_text(html_nodes(html_content, "#tpam td:nth-child(8)"))), date_convert))),
                  Amount=as.numeric(gsub("\r|\n|\t|,", "", html_text(html_nodes(html_content, "#tpam td:nth-child(9)")))))%>%
    mutate(Type=all_keyword[i])
  all_tender=rbind(all_tender, temp)
  print(i)
}
all_tender_sel=filter(all_tender, DeadlineDate>=today, !is.na(Amount), Amount<=AMOUNT_THRE)%>%
  group_by(OfficeName, CaseID, CaseName, DisseminationDate, DeadlineDate, Amount)%>%
  summarise(Type=paste(Type, collapse="、"))



